#!/usr/bin/env python3
"""Utility script to inspect log files inside an existing E2B sandbox."""

from __future__ import annotations

import argparse
import inspect
import os
import shlex
import sys
from typing import Optional

SandboxType = None

try:
    from e2b_code_interpreter import Sandbox as _CodeInterpreterSandbox

    SandboxType = _CodeInterpreterSandbox
except Exception:  # pragma: no cover - optional dependency
    _CodeInterpreterSandbox = None

if SandboxType is None:
    try:
        from e2b import Sandbox as _CoreSandbox

        SandboxType = _CoreSandbox
    except Exception:  # pragma: no cover - fail later with explicit message
        _CoreSandbox = None
else:
    try:
        # code interpreter sandbox on older SDKs misses resume helpers; prefer core sandbox instead
        from e2b import Sandbox as _CoreSandbox  # type: ignore

        if hasattr(_CoreSandbox, "_cls_connect") and not hasattr(SandboxType, "_cls_connect"):
            SandboxType = _CoreSandbox
    except Exception:
        _CoreSandbox = None

if SandboxType is None:  # pragma: no cover - defensive guard
    raise ImportError("Neither e2b_code_interpreter nor e2b Sandbox classes are available")

try:  # Align with e2b_sandbox_manager import path
    from e2b.sandbox.commands.command_handle import CommandExitException
except Exception:  # pragma: no cover - fallback when package layout changes
    try:
        from e2b_code_interpreter import CommandExitException  # type: ignore
    except Exception:
        class CommandExitException(Exception):
            """Fallback placeholder not expected to be raised."""

            pass


DEFAULT_LOG_DIR = "/home/user"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=
        "Print log file contents from an existing sandbox using the E2B API. "
        "Requires E2B_API_KEY to be configured.",
    )
    parser.add_argument(
        "sandbox_id",
        help="ID of the sandbox to inspect (e.g. sandbox_20240101_120000).",
    )
    parser.add_argument(
        "--path",
        default=f"{DEFAULT_LOG_DIR}/novnc.log",
        help="Absolute path of the log file inside the sandbox (default: /home/user/novnc.log).",
    )
    parser.add_argument(
        "--lines",
        type=int,
        default=200,
        help="Number of trailing lines to display (default: 200).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available *.log files in the log directory instead of printing a specific file.",
    )
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_LOG_DIR,
        help="Directory inside the sandbox to search when using --list (default: /home/user).",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Connect over HTTP instead of HTTPS when resuming the sandbox.",
    )
    parser.add_argument(
        "--exec",
        dest="exec_cmd",
        help="Run an arbitrary shell command inside the sandbox instead of reading logs.",
    )
    return parser


def ensure_api_key() -> None:
    if not os.environ.get("E2B_API_KEY"):
        sys.stderr.write("E2B_API_KEY environment variable is required to connect to the sandbox.\n")
        sys.exit(1)


def connect_sandbox(sandbox_id: str, secure: bool) -> SandboxType:  # type: ignore[valid-type]
    """Resume an existing sandbox regardless of SDK version."""

    Sandbox = SandboxType  # local alias for readability

    connect_kwargs = {}
    try:
        import inspect

        params = inspect.signature(Sandbox._cls_connect).parameters  # type: ignore[attr-defined]
        if "secure" in params:
            connect_kwargs["secure"] = secure
    except (AttributeError, ValueError):
        pass

    if hasattr(Sandbox, "_cls_connect"):
        sandbox = Sandbox._cls_connect(sandbox_id=sandbox_id, **connect_kwargs)  # type: ignore[attr-defined]
        sandbox.connect()
        return sandbox

    if hasattr(Sandbox, "connect"):
        try:
            params = inspect.signature(Sandbox.connect).parameters  # type: ignore[attr-defined]
            connect_kwargs = {k: v for k, v in connect_kwargs.items() if k in params}
        except (AttributeError, ValueError):
            connect_kwargs = {}

        resumed = Sandbox.connect(sandbox_id=sandbox_id, **connect_kwargs)  # type: ignore[misc]
        if isinstance(resumed, Sandbox):
            return resumed
    raise RuntimeError("This version of e2b SDK does not support resuming by sandbox_id.")


def run_command(sandbox: Sandbox, command: str) -> str:
    try:
        result = sandbox.commands.run(
            command,
            background=False,
            cwd="/home/user",
        )
    except CommandExitException as exc:  # pragma: no cover - defensive logging helper
        stderr = getattr(exc, "stderr", "") or str(exc)
        raise RuntimeError(f"Command failed inside sandbox: {stderr}") from exc

    if result.exit_code != 0:
        raise RuntimeError(
            f"Command exited with {result.exit_code}: {result.stderr or 'no stderr available'}",
        )

    return result.stdout


def list_logs(sandbox: Sandbox, log_dir: str) -> str:
    escaped_dir = shlex.quote(log_dir)
    cmd = f"bash -lc 'set -e; ls -1 {escaped_dir}/*.log 2>/dev/null'"
    output = run_command(sandbox, cmd)
    return output.strip() or "<no log files found>"


def tail_log(sandbox: Sandbox, path: str, lines: int) -> str:
    escaped_path = shlex.quote(path)
    cmd = (
        "bash -lc 'set -e; "
        f"if [ ! -f {escaped_path} ]; then echo "
        f"\"Log file not found: {escaped_path}\" >&2; exit 1; fi; "
        f"tail -n {lines} {escaped_path}'"
    )
    try:
        return run_command(sandbox, cmd)
    except RuntimeError as exc:
        message = str(exc)
        if "Log file not found" in message:
            hint = (
                "Log file not found. Use --list to see available logs or "
                "specify the correct path with --path."
            )
            raise RuntimeError(f"{message}\n{hint}") from exc
        raise


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ensure_api_key()

    sandbox = connect_sandbox(args.sandbox_id, secure=not args.insecure)

    if args.exec_cmd:
        output = run_command(sandbox, f"bash -lc {shlex.quote(args.exec_cmd)}")
    elif args.list:
        output = list_logs(sandbox, args.log_dir)
    else:
        output = tail_log(sandbox, args.path, args.lines)

    sys.stdout.write(output)
    if not output.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
