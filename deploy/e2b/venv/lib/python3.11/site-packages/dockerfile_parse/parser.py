# -*- coding: utf-8 -*-
"""
Copyright (c) 2015, 2018, 2019 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

import json
import logging
import os
import re
from contextlib import contextmanager
from shlex import quote

from .constants import DOCKERFILE_FILENAME, COMMENT_INSTRUCTION
from .util import (b2u, extract_key_values, get_key_val_dictionary,
                   u2b, Context, WordSplitter)


logger = logging.getLogger(__name__)


class KeyValues(dict):
    """
    Abstract base class for allowing direct write access to Dockerfile
    instructions which result in a set of key value pairs.

    Subclasses must override the `parser_attr` value.
    """
    parser_attr = None

    def __init__(self, key_values, parser):
        super(KeyValues, self).__init__(key_values)
        self.parser = parser

    def __delitem__(self, key):
        super(KeyValues, self).__delitem__(key)
        setattr(self.parser, self.parser_attr, dict(self))

    def __setitem__(self, key, value):
        super(KeyValues, self).__setitem__(key, value)
        setattr(self.parser, self.parser_attr, dict(self))

    def __eq__(self, other):
        if not isinstance(other, dict):
            return False
        return dict(self) == other

    def __hash__(self):
        return hash(json.dumps(self, separators=(',', ':'), sort_keys=True))


class Labels(KeyValues):
    """
    A class for allowing direct write access to Dockerfile labels, e.g.:

    parser.labels['label'] = 'value'
    """
    parser_attr = 'labels'


class Envs(KeyValues):
    """
    A class for allowing direct write access to Dockerfile env. vars., e.g.:

    parser.envs['variable_name'] = 'value'
    """
    parser_attr = 'envs'


class Args(KeyValues):
    """
    A class for allowing direct write access to Dockerfile build args, e.g.:

    parser.args['variable_name'] = 'value'
    """
    parser_attr = 'args'


class DockerfileParser(object):
    def __init__(self, path=None,
                 cache_content=False,
                 env_replace=True,
                 parent_env=None,
                 fileobj=None,
                 build_args=None):
        """
        Initialize source of Dockerfile
        :param path: path to (directory with) Dockerfile; if not provided,
                     and fileobj is not provided, the current working
                     directory will be used
        :param cache_content: cache Dockerfile content inside DockerfileParser
        :param env_replace: return content with variables replaced
        :param parent_env: python dict of inherited env vars from parent image
        :param fileobj: seekable file-like object containing Dockerfile content
                        as bytes (will be truncated on write)
        :param build_args: python dict of build args used when building image
        """

        self.fileobj = fileobj

        if self.fileobj is not None:
            if path is not None:
                raise ValueError("Parameters path and fileobj cannot be used together.")
            else:
                self.fileobj.seek(0)
        else:
            path = path or '.'
            if path.endswith(DOCKERFILE_FILENAME):
                self.dockerfile_path = path
            else:
                self.dockerfile_path = os.path.join(path, DOCKERFILE_FILENAME)

        self.cache_content = cache_content
        self.cached_content = ''  # unicode string

        if cache_content:
            try:
                # this will cache the Dockerfile content
                self.content
            except (IOError, OSError):
                # the Dockerfile doesn't exist yet
                pass

        self.env_replace = env_replace

        if parent_env is None:
            self.parent_env = {}
        else:
            assert isinstance(parent_env, dict)
            logger.debug("Setting inherited parent image ENV vars: %s", parent_env)
            self.parent_env = parent_env

        if build_args is None:
            self.build_args = {}
        else:
            assert isinstance(build_args, dict)
            logger.debug("Setting build args: %s", build_args)
            self.build_args = build_args

    @contextmanager
    def _open_dockerfile(self, mode):
        if self.fileobj is not None:
            self.fileobj.seek(0)
            if 'w' in mode:
                self.fileobj.truncate()
            yield self.fileobj
            self.fileobj.seek(0)
        else:
            with open(self.dockerfile_path, mode) as dockerfile:
                yield dockerfile

    @property
    def lines(self):
        """
        :return: list containing lines (unicode) from Dockerfile
        """
        if self.cache_content and self.cached_content:
            return self.cached_content.splitlines(True)

        try:
            with self._open_dockerfile('rb') as dockerfile:
                lines = [b2u(line) for line in dockerfile.readlines()]
                if self.cache_content:
                    self.cached_content = ''.join(lines)
                return lines
        except (IOError, OSError) as ex:
            logger.error("Couldn't retrieve lines from dockerfile: %r", ex)
            raise

    @lines.setter
    def lines(self, lines):
        """
        Fill Dockerfile content with specified lines
        :param lines: list of lines to be written to Dockerfile
        """
        if self.cache_content:
            self.cached_content = ''.join(b2u(line) for line in lines)

        try:
            with self._open_dockerfile('wb') as dockerfile:
                dockerfile.writelines(u2b(line) for line in lines)
        except (IOError, OSError) as ex:
            logger.error("Couldn't write lines to dockerfile: %r", ex)
            raise

    @property
    def content(self):
        """
        :return: string (unicode) with Dockerfile content
        """
        if self.cache_content and self.cached_content:
            return self.cached_content

        try:
            with self._open_dockerfile('rb') as dockerfile:
                content = b2u(dockerfile.read())
                if self.cache_content:
                    self.cached_content = content
                return content
        except (IOError, OSError) as ex:
            logger.error("Couldn't retrieve content of dockerfile: %r", ex)
            raise

    @content.setter
    def content(self, content):
        """
        Overwrite Dockerfile with specified content
        :param content: string to be written to Dockerfile
        """
        if self.cache_content:
            self.cached_content = b2u(content)

        try:
            with self._open_dockerfile('wb') as dockerfile:
                dockerfile.write(u2b(content))
        except (IOError, OSError) as ex:
            logger.error("Couldn't write content to dockerfile: %r", ex)
            raise

    @property
    def structure(self):
        """
        Returns a list of dicts describing the commands:
        [
            {"instruction": "FROM",       # always upper-case
             "startline": 0,              # 0-based
             "endline": 0,                # 0-based
             "content": "From fedora\n",
             "value": "fedora"},

            {"instruction": "CMD",
             "startline": 1,
             "endline": 2,
             "content": "CMD yum -y update && \\\n    yum clean all\n",
             "value": "yum -y update && yum clean all"}
        ]
        """
        def _rstrip_eol(text, line_continuation_char='\\'):
            text = text.rstrip()
            if text.endswith(line_continuation_char):
                return text[:-1]
            return text

        def _create_instruction_dict(instruction=None, value=None):
            return {
                'instruction': instruction,
                'startline': lineno,
                'endline': lineno,
                'content': line,  # pylint: disable=undefined-loop-variable
                'value': value
            }

        def _clean_comment_line(line):
            line = re.sub(r'^\s*#\s*', '', line)
            line = re.sub(r'\n', '', line)
            return line

        instructions = []
        lineno = -1
        line_continuation_char = '\\'
        insnre = re.compile(r'^\s*(\S+)\s+(.*)$')  # matched group is insn
        contre = re.compile(r'^.*\\\s*$')          # line continues?
        commentre = re.compile(r'^\s*#')           # line is a comment?
        directive_possible = True
        # escape directive regex
        escape_directive_re = re.compile(r'^\s*#\s*escape\s*=\s*(\\|`)\s*$', re.I)
        # syntax directive regex
        syntax_directive_re = re.compile(r'^\s*#\s*syntax\s*=\s*(.*)\s*$', re.I)

        in_continuation = False
        current_instruction = {}

        for line in self.lines:
            lineno += 1

            if directive_possible:
                # once support for python versions before 3.8 is dropped use walrus operator
                if escape_directive_re.match(line):
                    # Do the matching twice if there is a directive to avoid doing the matching
                    # for other lines
                    match = escape_directive_re.match(line)
                    line_continuation_char = match.group(1)
                    contre = re.compile(r'^.*' + re.escape(match.group(1)) + r'\s*$')
                elif syntax_directive_re.match(line):
                    # Currently no information for the syntax directive is stored it is still
                    # necessary to detect escape directives after a syntax directive
                    pass
                else:
                    directive_possible = False

            # It is necessary to keep instructions and comment parsing separate,
            # as a multi-line instruction can be interjected with comments.
            if commentre.match(line):
                comment = _create_instruction_dict(
                    instruction=COMMENT_INSTRUCTION,
                    value=_clean_comment_line(line)
                )
                instructions.append(comment)

            else:
                if not in_continuation:
                    m = insnre.match(line)
                    if not m:
                        continue
                    current_instruction = _create_instruction_dict(
                        instruction=m.groups()[0].upper(),
                        value=_rstrip_eol(m.groups()[1], line_continuation_char)
                    )
                else:
                    current_instruction['content'] += line
                    current_instruction['endline'] = lineno

                    if current_instruction['value']:
                        current_instruction['value'] += _rstrip_eol(line, line_continuation_char)
                    else:
                        current_instruction['value'] = _rstrip_eol(line.lstrip(),
                                                                   line_continuation_char)

                in_continuation = contre.match(line)
                if not in_continuation and current_instruction:
                    instructions.append(current_instruction)

        return instructions

    @property
    def json(self):
        """
        :return: JSON formatted string with instructions & values from Dockerfile
        """
        insndescs = [{insndesc['instruction']: insndesc['value']} for insndesc in self.structure]
        return json.dumps(insndescs)

    @property
    def parent_images(self):
        """
        :return: list of parent images -- one image per each stage's FROM instruction
        """
        in_stage = False
        top_args = {}
        parents = []
        for instr in self.structure:
            if instr['instruction'] == 'ARG':
                if not in_stage:
                    key_val_list = extract_key_values(
                        env_replace=False,
                        args={}, envs={},
                        instruction_value=instr['value'])
                    for key, value in key_val_list:
                        if key in self.build_args:
                            value = self.build_args[key]
                        top_args[key] = value
            elif instr['instruction'] == 'FROM':
                in_stage = True
                image, _ = image_from(instr['value'])
                if image is not None:
                    image = WordSplitter(image, args=top_args).dequote()
                    parents.append(image)
        return parents

    @parent_images.setter
    def parent_images(self, parents):
        """
        setter for images in 'FROM' instructions.
        Images are updated per build stage with the given parents in the order they appear.
        Raises RuntimeError if a different number of parents are given than there are stages
        as that is likely to be a mistake.

        :param parents: list of image strings
        """
        parents = list(parents)
        change_instrs = []
        for instr in self.structure:
            if instr['instruction'] != 'FROM':
                continue

            old_image, stage = image_from(instr['value'])
            if old_image is None:
                continue  # broken FROM, fixing would just confuse things
            if not parents:
                raise RuntimeError("not enough parents to match build stages")

            image = parents.pop(0)
            if image != old_image:
                instr['value'] = '{0} AS {1}'.format(image, stage) if stage else image
                instr['content'] = 'FROM {0}\n'.format(instr['value'])
                change_instrs.append(instr)

        if parents:
            raise RuntimeError("trying to update too many parents for build stages")

        lines = self.lines
        for instr in reversed(change_instrs):
            lines[instr['startline']:instr['endline']+1] = [instr['content']]

        self.lines = lines

    @property
    def is_multistage(self):
        return len(self.parent_images) > 1

    @property
    def baseimage(self):
        """
        :return: base image, i.e. value of final stage FROM instruction
        """
        return (self.parent_images or [None])[-1]

    @baseimage.setter
    def baseimage(self, new_image):
        """
        change image of final stage FROM instruction
        """
        images = []
        for instr in self.structure:
            if instr['instruction'] == 'FROM':
                image, _ = image_from(instr['value'])
                if image is not None:
                    images.append(image)
        if not images:
            raise RuntimeError('No stage defined to set base image on')
        images[-1] = new_image
        self.parent_images = images

    @property
    def cmd(self):
        """
        Determine the final CMD instruction, if any, in the final build stage.
        CMDs from earlier stages are ignored.
        :return: value of final stage CMD instruction
        """
        value = None
        for insndesc in self.structure:
            if insndesc['instruction'] == 'FROM':  # new stage, reset
                value = None
            elif insndesc['instruction'] == 'CMD':
                value = insndesc['value']
        return value

    @cmd.setter
    def cmd(self, value):
        """
        setter for final 'CMD' instruction in final build stage

        """
        cmd = None
        for insndesc in self.structure:
            if insndesc['instruction'] == 'FROM':  # new stage, reset
                cmd = None
            elif insndesc['instruction'] == 'CMD':
                cmd = insndesc

        new_cmd = 'CMD ' + value
        if cmd:
            self.add_lines_at(cmd, new_cmd, replace=True)
        else:
            self.add_lines(new_cmd)

    @property
    def labels(self):
        """
        LABELs from Dockerfile
        :return: dictionary of label:value (value might be '')
        """
        return self._instruction_getter('LABEL', env_replace=self.env_replace)

    @property
    def envs(self):
        """
        ENVs from Dockerfile
        :return: dictionary of env_var_name:value (value might be '')
        """
        return self._instruction_getter('ENV', env_replace=self.env_replace)

    @property
    def args(self):
        """
        ARGs from Dockerfile
        :return: dictionary of arg_var_name:value (value might be '')
        """
        return self._instruction_getter('ARG', env_replace=self.env_replace)

    def _instruction_getter(self, name, env_replace):
        """
        Get LABEL or ENV or ARG instructions with environment replacement

        :param name: e.g. 'LABEL' or 'ENV' or 'ARG'
        :param env_replace: bool, whether to perform ENV substitution
        :return: Labels instance or Envs instance
        """
        if name not in ('LABEL', 'ENV', 'ARG'):
            raise ValueError("Unsupported instruction '{0}'".format(name))
        in_stage = False
        top_args = {}
        instructions = {}
        args = {}
        envs = {}

        for instruction_desc in self.structure:
            this_instruction = instruction_desc['instruction']
            if this_instruction == 'FROM':
                in_stage = True
                instructions.clear()
                args = {}
                envs = self.parent_env.copy()
            elif this_instruction in (name, 'ENV', 'ARG'):
                logger.debug("%s value: %r", name.lower(), instruction_desc['value'])
                key_val_list = extract_key_values(
                    env_replace=this_instruction != 'ARG' and env_replace,
                    args=args, envs=envs,
                    instruction_value=instruction_desc['value'])
                for key, value in key_val_list:
                    if this_instruction == 'ARG':
                        if in_stage:
                            if key in top_args:
                                value = top_args[key]
                            elif key in self.build_args:
                                value = self.build_args[key]
                            args[key] = value
                        else:
                            if key in self.build_args:
                                value = self.build_args[key]
                            top_args[key] = value
                    if this_instruction == name:
                        instructions[key] = value
                        logger.debug("new %s %r=%r", name.lower(), key, value)
                    if this_instruction == 'ENV':
                        envs[key] = value

        logger.debug("instructions: %r", instructions)
        if name == 'LABEL':
            return Labels(instructions, self)
        elif name == 'ENV':
            return Envs(instructions, self)
        else:
            return Args(instructions, self)

    @labels.setter
    def labels(self, labels):
        """
        Setter for LABEL instruction, i.e. sets LABELs per input param.
        :param labels: dictionary of label name & value to be set
        """
        self._instructions_setter('LABEL', labels)

    @envs.setter
    def envs(self, envs):
        """
        Setter for ENV instruction, i.e. sets ENVs per input param.
        :param envs: dictionary of env. var. name & value to be set
        """
        self._instructions_setter('ENV', envs)

    @args.setter
    def args(self, args):
        """
        Setter for ARG instruction, i.e. sets ARGs per input param.
        :param args: dictionary of arg names & values to be set
        """
        self._instructions_setter('ARG', args)

    def _instructions_setter(self, name, instructions):
        if not isinstance(instructions, dict):
            raise TypeError('instructions needs to be a dictionary {name: value}')

        if name == 'LABEL':
            existing = self.labels
        elif name == 'ENV':
            existing = self.envs
        elif name == 'ARG':
            existing = self.args
        else:
            raise ValueError("Unexpected instruction '%s'" % name)

        logger.debug("setting %s instructions: %r", name, instructions)

        to_delete = [k for k in existing if k not in instructions]
        for key in to_delete:
            logger.debug("delete %r", key)
            self._modify_instruction_label_env(name, key, None)

        to_add = dict((k, v) for (k, v) in instructions.items() if k not in existing)
        for k, v in to_add.items():
            logger.debug("add %r", k)
            self._add_instruction(name, (k, v))

        to_change = dict((k, v) for (k, v) in instructions.items()
                         if (k in existing and v != existing[k]))
        for k, v in to_change.items():
            logger.debug("modify %r", k)
            self._modify_instruction_label_env(name, k, v)

    def _modify_instruction_label(self, label_key, instr_value):
        self._modify_instruction_label_env('LABEL', label_key, instr_value)

    def _modify_instruction_env(self, env_var_key, env_var_value):
        self._modify_instruction_label_env('ENV', env_var_key, env_var_value)

    def _modify_instruction_arg(self, arg_key, arg_value):
        self._modify_instruction_label_env('ARG', arg_key, arg_value)

    def _modify_instruction_label_env(self, instruction, instr_key, instr_value):
        """
        set <INSTRUCTION> instr_key to instr_value

        :param instr_key: str, label key
        :param instr_value: str or None, new label/env value or None to remove
        """
        if instruction == 'LABEL':
            instructions = self.labels
        elif instruction == 'ENV':
            instructions = self.envs
        elif instruction == 'ARG':
            instructions = self.args
        else:
            raise ValueError("Unknown instruction '%s'" % instruction)

        if instr_key not in instructions:
            raise KeyError('%s not in %ss' % (instr_key, instruction))

        # extract target instructions from the final stage only
        candidates = []
        for insn in self.structure:
            if insn['instruction'] == 'FROM':
                candidates = []
            if insn['instruction'] == instruction:
                candidates.append(insn)

        # Find where in the file to put the changes
        content = startline = endline = None
        for candidate in candidates:
            words = list(WordSplitter(candidate['value']).split(dequote=False))

            # LABEL/ENV/ARG syntax is one of two types:
            if '=' not in words[0]:  # LABEL/ENV/ARG name value
                # Remove quotes from key name and see if it's the one
                # we're looking for.
                if WordSplitter(words[0]).dequote() == instr_key:
                    if instr_value is None:
                        # Delete this line altogether
                        content = None
                    else:
                        # Adjust label/env value
                        words[1:] = [quote(instr_value)]

                        # Now reconstruct the line
                        content = " ".join([instruction] + words) + '\n'

                    startline = candidate['startline']
                    endline = candidate['endline']
                    break
            else:  # LABEL/ENV/ARG "name"="value"
                for index, token in enumerate(words):
                    key, _ = token.split("=", 1)
                    if WordSplitter(key).dequote() == instr_key:
                        if instr_value is None:
                            # Delete this label
                            del words[index]
                        else:
                            # Adjust label/env value
                            words[index] = "{0}={1}".format(key,
                                                            quote(instr_value))

                        if len(words) == 0:
                            # We removed the last label/env, delete the whole line
                            content = None
                        else:
                            # Now reconstruct the line
                            content = " ".join([instruction] + words) + '\n'

                        startline = candidate['startline']
                        endline = candidate['endline']
                        break

        # We know the label/env we're looking for is there
        assert startline and endline

        # Re-write the Dockerfile
        lines = self.lines
        del lines[startline:endline + 1]
        if content:
            lines.insert(startline, content)
        self.lines = lines

    def _delete_instructions(self, instruction, value=None):
        """
        :param instruction: name of instruction to be deleted
        :param value: if specified, delete instruction only when it has this value
                      if instruction is LABEL then value is label name
        """
        if instruction == 'LABEL' and value:
            self._modify_instruction_label(value, None)
            return
        if instruction == 'ENV' and value:
            self._modify_instruction_env(value, None)
            return
        if instruction == 'ARG' and value:
            self._modify_instruction_arg(value, None)
            return

        lines = self.lines
        deleted = False
        for insn in reversed(self.structure):
            if insn['instruction'] == instruction:
                if value and insn['value'] != value:
                    continue
                deleted = True
                del lines[insn['startline']:insn['endline'] + 1]
        if deleted:
            self.lines = lines

    def _add_instruction(self, instruction, value):
        """
        :param instruction: instruction name to be added
        :param value: instruction value
        """
        if instruction in ('LABEL', 'ENV', 'ARG') and len(value) == 2:
            new_line = instruction + ' ' + '='.join(map(quote, value)) + '\n'
        else:
            new_line = '{0} {1}\n'.format(instruction, value)
        if new_line:
            lines = self.lines
            if not lines[len(lines) - 1].endswith('\n'):
                new_line = '\n' + new_line
            lines += new_line
            self.lines = lines

    def add_lines(self, *lines, **kwargs):
        """
        Add lines to the beginning or end of the build.
        :param lines: one or more lines to add to the content, by default at the end.
        :param all_stages: bool for whether to add in all stages for a multistage build
                           or (by default) only the last.
        :param at_start: adds at the beginning (after FROM) of the stage(s) instead of the end.
        :param skip_scratch: skip stages which use "FROM scratch"
        """
        assert len(lines) > 0
        lines = [_endline(line) for line in lines]
        all_stages = kwargs.pop('all_stages', False)
        at_start = kwargs.pop('at_start', False)
        skip_scratch = kwargs.pop('skip_scratch', False)
        assert not kwargs, "Unknown keyword argument(s): {0}".format(list(kwargs))

        froms = [
            instr for instr in self.structure
            if instr['instruction'] == 'FROM'
        ] or [{'endline': -1}]  # no FROM? fake one before the beginning
        if not all_stages:  # only modify the last
            froms = [froms[-1]]

        df_lines = self.lines
        # make sure last line has a newline if lines are to be appended
        if df_lines and not at_start:
            df_lines[-1] = _endline(df_lines[-1])

        # iterate through the stages in reverse order
        # so adding lines doesn't invalidate line numbers from structure dicts.
        # first add a bogus instruction to represent EOF in our iteration.
        froms.append({'startline': len(df_lines) + 1})
        for stage in range(len(froms)-2, -1, -1):  # e.g. 0 for single or 2, 1, 0 for 3 stages
            start, finish = froms[stage], froms[stage+1]
            linenum = start['endline'] + 1 if at_start else finish['startline']
            image, _ = image_from(froms[stage].get('value') or '')
            if skip_scratch and image == 'scratch':
                continue
            df_lines[linenum:linenum] = lines

        self.lines = df_lines

    def add_lines_at(self, anchor, *lines, **kwargs):
        """
        Add lines at a specific location in the file.
        :param anchor: structure_dict|line_str|line_num a reference to where adds should occur
        :param lines: one or more lines to add to the content
        :param replace: if True -- replace the anchor
        :param after: if True -- insert after the anchor (conflicts with "replace")
        """
        assert len(lines) > 0
        replace = kwargs.pop('replace', False)
        after = kwargs.pop('after', False)
        assert not (after and replace)
        assert not kwargs, "Unknown keyword argument(s): {0}".format(list(kwargs))

        # find the line number for the insertion
        df_lines = self.lines
        if isinstance(anchor, int):  # line number, just validate
            assert 0 <= anchor < len(df_lines)
            if replace:
                del df_lines[anchor]
        elif isinstance(anchor, dict):  # structure
            assert anchor in self.structure, "Current structure does not match: {0}".format(anchor)
            if replace:
                df_lines[anchor['startline']:anchor['endline'] + 1] = []
            if after:
                anchor = anchor['endline']
            else:
                anchor = anchor['startline']
        elif isinstance(anchor, str):  # line contents
            matches = [index for index, text in enumerate(df_lines) if text == anchor]
            if not matches:
                raise RuntimeError("Cannot find line in the build file:\n" + anchor)
            anchor = matches[-1]
            if replace:
                del df_lines[anchor]
        else:
            raise RuntimeError("Unknown anchor type {0}".format(anchor))

        if after:
            # ensure there's a newline on final line
            df_lines[anchor] = _endline(df_lines[anchor])
            anchor += 1

        df_lines[anchor:anchor] = [_endline(line) for line in lines]
        self.lines = df_lines

    @property
    def context_structure(self):
        """
        :return: list of Context objects
            (Contains info about build arguments, labels, and environment variables for each line.)
        """
        in_stage = False
        top_args = {}
        instructions = []
        last_context = Context()
        for instr in self.structure:
            instruction_type = instr['instruction']
            if instruction_type == "FROM":  # reset per stage
                in_stage = True
                last_context = Context(envs=dict(self.parent_env))

            context = Context(args=dict(last_context.args),
                              envs=dict(last_context.envs),
                              labels=dict(last_context.labels))

            if instruction_type in ('ARG', 'ENV', 'LABEL'):
                values = get_key_val_dictionary(
                    instruction_value=instr['value'],
                    env_replace=instruction_type != 'ARG' and self.env_replace,
                    args=last_context.args,
                    envs=last_context.envs)
                if instruction_type == 'ARG' and self.env_replace:
                    if in_stage:
                        for key in list(values.keys()):
                            if key in top_args:
                                values[key] = top_args[key]
                            elif key in self.build_args:
                                values[key] = self.build_args[key]
                    else:
                        for key, value in list(values.items()):
                            if key in self.build_args:
                                value = self.build_args[key]
                            top_args[key] = value
                            values[key] = value
                context.set_line_value(context_type=instruction_type, value=values)

            instructions.append(context)
            last_context = context
        return instructions


def image_from(from_value):
    """
    :param from_value: string like "image:tag" or "image:tag AS name"
    :return: tuple of the image and stage name, e.g. ("image:tag", None)
    """
    regex = re.compile(r"""(?xi)        # readable, case-insensitive regex
        \s*                             # ignore leading whitespace
        (?P<platform> --platform=\S+)?  # optional platform parameter
        \s*                             # more whitespaces
        (?P<image> \S+ )                # image and optional tag
        (?:                             # optional "AS name" clause for stage
            \s+ AS \s+
            (?P<name> \S+ )
        )?
        """)
    match = re.match(regex, from_value)
    return match.group('image', 'name') if match else (None, None)


def _endline(line):
    """
    Make sure the line ends with a single newline.
    Since trailing whitespace has no significance, remove it.
    """
    return line.rstrip() + '\n'
