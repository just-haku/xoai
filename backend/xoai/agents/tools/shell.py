"""Shell execution tool — auto-sources user venv."""

import subprocess
from xoai.workspace.service import get_user_workspace
from xoai.workspace.venv import get_venv_activate_cmd


async def execute_command(user_id: str, command: str, timeout: int = 300) -> str:
    workspace = get_user_workspace(user_id)
    venv_cmd = get_venv_activate_cmd(user_id)
    full_cmd = f"{venv_cmd} && {command}"

    try:
        result = subprocess.run(
            full_cmd, shell=True, cwd=workspace,
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout + ("\n[stderr]\n" + result.stderr if result.stderr else "")
        return output[-3000:] if len(output) > 3000 else (output.strip() or "Command success.")
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s."
    except Exception as e:
        return f"Error: {e}"
