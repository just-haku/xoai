"""Workspace service: path jail, quota enforcement, file operations."""

import os
import hashlib

from xoai.config import settings

QUOTA_LIMIT_BYTES = 15 * 1024 * 1024 * 1024  # 15GB


def get_user_workspace(user_id: str) -> str:
    """Return the absolute workspace path for a user."""
    return os.path.join(settings.xoai_storage, "users", user_id, "workspace")


def get_user_venv(user_id: str) -> str:
    """Return the venv path for a user."""
    return os.path.join(settings.xoai_storage, "users", user_id, "venv")


def resolve_safe_path(user_id: str, relative_path: str) -> str:
    """Resolve a path safely within the user's workspace. Prevents directory traversal."""
    workspace = get_user_workspace(user_id)
    os.makedirs(workspace, exist_ok=True)

    # Resolve to absolute and verify it's within workspace
    requested = os.path.realpath(os.path.join(workspace, relative_path))
    workspace_real = os.path.realpath(workspace)

    if not requested.startswith(workspace_real + os.sep) and requested != workspace_real:
        raise PermissionError(f"Path escapes workspace: {relative_path}")

    return requested


def calculate_dir_size(path: str) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total


def check_quota(user_id: str, additional_bytes: int = 0) -> bool:
    """Check if a user's workspace is within quota."""
    workspace = get_user_workspace(user_id)
    if not os.path.exists(workspace):
        return True
    current = calculate_dir_size(workspace)
    return (current + additional_bytes) <= QUOTA_LIMIT_BYTES


def file_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
