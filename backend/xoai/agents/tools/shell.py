"""Shell execution tool with allowlisted commands and scrubbed environment."""

from __future__ import annotations

import os
import shlex
import subprocess

from xoai.metrics import metrics
from xoai.workspace.service import get_user_venv, get_user_workspace

ALLOWED_COMMANDS = {
    "ls",
    "pwd",
    "cat",
    "head",
    "tail",
    "find",
    "rg",
    "python",
    "python3",
    "pytest",
    "git",
}
MAX_TIMEOUT_SECONDS = 120
MAX_OUTPUT_BYTES = 3000
SAFE_ENV_KEYS = {"HOME", "LANG", "LC_ALL", "PATH", "PYTHONPATH"}


def _build_env(user_id: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key in SAFE_ENV_KEYS}
    venv_bin = os.path.join(get_user_venv(user_id), "bin")
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}".rstrip(":")
    env["VIRTUAL_ENV"] = os.path.dirname(venv_bin)
    return env


def _parse_command(command: str) -> list[str]:
    parts = shlex.split(command)
    if not parts:
        raise ValueError("Command is empty.")
    executable = parts[0]
    if executable not in ALLOWED_COMMANDS:
        raise ValueError(f"Command '{executable}' is not allowed.")
    return parts


async def execute_command(user_id: str, command: str, timeout: int = 60) -> str:
    workspace = get_user_workspace(user_id)
    try:
        args = _parse_command(command)
        result = subprocess.run(
            args,
            cwd=workspace,
            env=_build_env(user_id),
            capture_output=True,
            text=True,
            timeout=min(timeout, MAX_TIMEOUT_SECONDS),
        )
        output = (result.stdout or "") + ("\n[stderr]\n" + result.stderr if result.stderr else "")
        output = output.strip() or "Command success."
        metrics.incr("tools.shell.executed")
        return output[-MAX_OUTPUT_BYTES:]
    except subprocess.TimeoutExpired:
        metrics.incr("tools.shell.timeout")
        return f"Error: command timed out after {min(timeout, MAX_TIMEOUT_SECONDS)}s."
    except Exception as exc:
        metrics.incr("tools.shell.denied")
        return f"Error: {exc}"

