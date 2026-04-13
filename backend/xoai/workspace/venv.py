"""Per-user Python venv provisioning."""

import os
import subprocess
import logging

from xoai.workspace.service import get_user_venv

logger = logging.getLogger("xoai.workspace.venv")


def ensure_venv(user_id: str) -> str:
    """Create a venv for the user if it doesn't exist. Returns venv path."""
    venv_path = get_user_venv(user_id)
    if not os.path.exists(os.path.join(venv_path, "bin", "activate")):
        logger.info(f"Provisioning venv for user {user_id}...")
        os.makedirs(venv_path, exist_ok=True)
        subprocess.run(
            ["python3", "-m", "venv", venv_path],
            check=True,
            capture_output=True,
        )
        logger.info(f"✅ Venv ready: {venv_path}")
    return venv_path


def get_venv_activate_cmd(user_id: str) -> str:
    """Return the shell command prefix to activate the user's venv."""
    venv_path = get_user_venv(user_id)
    return f"source {venv_path}/bin/activate"
