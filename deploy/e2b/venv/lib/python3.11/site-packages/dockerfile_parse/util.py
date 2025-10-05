# -*- coding: utf-8 -*-
"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from io import StringIO


def b2u(string):
    """ bytes to unicode """
    if isinstance(string, bytes):
        return string.decode('utf-8')
    return string


def u2b(string):
    """ unicode to bytes"""
    if isinstance(string, str):
        return string.encode('utf-8')
    return string


class WordSplitter(object):
    """
    Split string into words, substituting environment variables if provided

    Methods defined here:

    dequote()
        Returns the string with escaped and quotes consumed

    split(maxsplit=None, dequote=True)
        Returns an iterable of words, split at whitespace
    """

    SQUOTE = "'"
    DQUOTE = '"'

    def __init__(self, s, args=None, envs=None):
        """
        :param s: str, string to process
        :param args: dict, build arguments to use; if None, do not
            attempt substitution
        :param envs: dict, environment variables to use; if None, do not
            attempt substitution
        """
        self.stream = StringIO(s)
        self.args = args
        self.envs = envs

        # Initial state
        self.quotes = None  # the quoting character in force, or None
        self.escaped = False

    def _update_quoting_state(self, ch):
        """
        Update self.quotes and self.escaped

        :param ch: str, current character
        :return: ch if it was not used to update quoting state, else ''
        """

        # Set whether the next character is escaped
        # Unquoted:
        #   a backslash escapes the next character
        # Double-quoted:
        #   a backslash escapes the next character only if it is a double-quote
        # Single-quoted:
        #   a backslash is not special
        is_escaped = self.escaped
        self.escaped = (not self.escaped and
                        ch == '\\' and
                        self.quotes != self.SQUOTE)
        if self.escaped:
            return ''

        if is_escaped:
            if self.quotes == self.DQUOTE:
                if ch == '"':
                    return ch
                return "{0}{1}".format('\\', ch)

            return ch

        if self.quotes is None:
            if ch in (self.SQUOTE, self.DQUOTE):
                self.quotes = ch
                return ''

        elif self.quotes == ch:
            self.quotes = None
            return ''

        return ch

    def dequote(self):
        return ''.join(self.split(maxsplit=0))

    def split(self, maxsplit=None, dequote=True):
        """
        Generator for the words of the string

        :param maxsplit: perform at most maxsplit splits;
            if None, do not limit the number of splits
        :param dequote: remove quotes and escape characters once consumed
        """

        class Word(object):
            """
            A None-or-str object which can always be appended to.
            Similar to a defaultdict but with only a single value.
            """

            def __init__(self):
                self.value = None

            @property
            def valid(self):
                return self.value is not None

            def append(self, s):
                if self.value is None:
                    self.value = s
                else:
                    self.value += s

        num_splits = 0
        word = Word()
        while True:
            ch = self.stream.read(1)
            if not ch:
                # EOF
                if word.valid:
                    yield word.value

                return

            if (not self.escaped and
                    (self.envs is not None or self.args is not None) and
                    ch == '$' and
                    self.quotes != self.SQUOTE):
                while True:
                    # Substitute environment variable
                    braced = False
                    varname = ''
                    while True:
                        ch = self.stream.read(1)
                        if varname == '' and ch == '{':
                            braced = True
                            continue

                        if not ch:
                            # EOF
                            break

                        if braced and ch == '}':
                            break

                        if not ch.isalnum() and ch != '_':
                            break

                        varname += ch

                    if self.envs is not None and varname in self.envs:
                        word.append(self.envs[varname])
                    elif self.args is not None and varname in self.args:
                        word.append(self.args[varname])

                    # Check whether there is another envvar
                    if ch != '$':
                        break

                if braced and ch == '}':
                    continue

                # ch now holds the next character

            # Figure out what our quoting/escaping state will be
            # after this character
            is_escaped = self.escaped
            ch_unless_consumed = self._update_quoting_state(ch)

            if dequote:
                # If we just processed a quote or escape character,
                # and were asked to dequote the string, consume it now
                ch = ch_unless_consumed

            # If word-splitting has been requested, check whether we are
            # at a whitespace character
            may_split = maxsplit != 0 and (maxsplit is None or
                                           num_splits < maxsplit)
            at_split = may_split and (self.quotes is None and
                                      not is_escaped and
                                      ch.isspace())
            if at_split:
                # It is time to yield a word
                if word.valid:
                    num_splits += 1
                    yield word.value

                word = Word()
            else:
                word.append(ch)


def extract_key_values(env_replace, args, envs, instruction_value):
    words = list(WordSplitter(instruction_value).split(dequote=False))
    key_val_list = []

    def substitute_vars(val):
        kwargs = {}
        if env_replace:
            kwargs['args'] = args
            kwargs['envs'] = envs

        return WordSplitter(val, **kwargs).dequote()

    if '=' not in words[0]:
        # This form is:
        #   LABEL/ENV name value
        # The first word is the name, remainder are the value.
        key_val = [substitute_vars(x) for x in instruction_value.split(None, 1)]
        key = key_val[0]
        try:
            val = key_val[1]
        except IndexError:
            val = ''

        key_val_list.append((key, val))
    else:
        # This form is:
        #   LABEL/ENV "name"="value" ["name"="value"...]
        # Each word is a key=value pair.
        for k_v in words:
            if '=' not in k_v:
                raise ValueError('Syntax error - can\'t find = in "{word}". '
                                 'Must be of the form: name=value'
                                 .format(word=k_v))
            key, val = [substitute_vars(x) for x in k_v.split('=', 1)]
            key_val_list.append((key, val))

    return key_val_list


def get_key_val_dictionary(instruction_value, env_replace=False, args=None, envs=None):
    args = args or {}
    envs = envs or {}
    return dict(extract_key_values(instruction_value=instruction_value,
                                   env_replace=env_replace,
                                   args=args, envs=envs))


class Context(object):
    def __init__(self, args=None, envs=None, labels=None,
                 line_args=None, line_envs=None, line_labels=None):
        """
        Class representing current state of build arguments, environment variables and labels.

        :param args: dict with arguments valid for this line
            (all variables defined to this line)
        :param envs: dict with variables valid for this line
            (all variables defined to this line)
        :param labels: dict with labels valid for this line
            (all labels defined to this line)
        :param line_args: dict with arguments defined on this line
        :param line_envs: dict with variables defined on this line
        :param line_labels: dict with labels defined on this line
        """
        self.args = args or {}
        self.envs = envs or {}
        self.labels = labels or {}
        self.line_args = line_args or {}
        self.line_envs = line_envs or {}
        self.line_labels = line_labels or {}

    def set_line_value(self, context_type, value):
        """
        Set value defined on this line ('line_args'/'line_envs'/'line_labels')
        and update 'args'/'envs'/'labels'.

        :param context_type: "ARG" or "ENV" or "LABEL"
        :param value: new value for this line
        """
        if context_type.upper() == "ARG":
            self.line_args = value
            self.args.update(value)
        elif context_type.upper() == "ENV":
            self.line_envs = value
            self.envs.update(value)
        elif context_type.upper() == "LABEL":
            self.line_labels = value
            self.labels.update(value)
        else:
            raise ValueError("Unexpected context type: " + context_type)

    def get_line_value(self, context_type):
        """
        Get the values defined on this line.

        :param context_type: "ARG" or "ENV" or "LABEL"
        :return: values of given type defined on this line
        """
        if context_type.upper() == "ARG":
            return self.line_args
        if context_type.upper() == "ENV":
            return self.line_envs
        if context_type.upper() == "LABEL":
            return self.line_labels
        raise ValueError("Unexpected context type: " + context_type)

    def get_values(self, context_type):
        """
        Get the values valid on this line.

        :param context_type: "ARG" or "ENV" or "LABEL"
        :return: values of given type valid on this line
        """
        if context_type.upper() == "ARG":
            return self.args
        if context_type.upper() == "ENV":
            return self.envs
        if context_type.upper() == "LABEL":
            return self.labels
        raise ValueError("Unexpected context type: " + context_type)
