"""Workspace service: path jail, quota enforcement, file operations."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone

from xoai.config import settings
from xoai.storage_gc import track_storage_artifact, untrack_storage_artifact

QUOTA_LIMIT_BYTES = 5 * 1024 * 1024 * 1024  # 5GB default
ADMIN_QUOTA_BYPASS = True
logger = logging.getLogger("xoai.workspace.service")


def get_user_workspace(user_id: str) -> str:
    """Return the absolute workspace path for a user."""
    return os.path.join(settings.xoai_storage, "users", user_id, "workspace")


def get_user_venv(user_id: str) -> str:
    """Return the venv path for a user."""
    return os.path.join(settings.xoai_storage, "users", user_id, "venv")


def get_user_upload_tmp(user_id: str) -> str:
    return os.path.join(settings.xoai_storage, "users", user_id, "tmp", "uploads")


def resolve_safe_path(user_id: str, relative_path: str, workspace: str = None) -> str:
    """Resolve a path safely within the user's workspace. Prevents directory traversal."""
    if not workspace:
        workspace = get_user_workspace(user_id)
    if not os.path.isdir(workspace):
        os.makedirs(workspace, exist_ok=True)

    normalized_relative = relative_path or ""
    requested = os.path.abspath(os.path.join(workspace, relative_path))
    workspace_real = os.path.abspath(workspace)
    common_prefix = os.path.commonprefix([workspace_real + os.sep, requested + os.sep])

    try:
        if (
            os.path.commonpath([workspace_real, requested]) != workspace_real
            or common_prefix.rstrip(os.sep) != workspace_real.rstrip(os.sep)
            or normalized_relative.startswith("../")
            or "/../" in normalized_relative
            or normalized_relative == ".."
        ):
            raise PermissionError(f"Path escapes workspace: {relative_path}")
    except ValueError:
        raise PermissionError(f"Path escapes workspace: {relative_path}")

    return requested


def ensure_not_workspace_root(path: str, workspace: str, operation: str) -> None:
    if os.path.abspath(path) == os.path.abspath(workspace):
        raise PermissionError(f"Refusing to {operation} the workspace root")


def get_admin_workspace() -> str:
    workspace = settings.admin_workspace_path
    if not workspace:
        raise PermissionError("Admin workspace is not configured")
    workspace = os.path.abspath(workspace)
    if not os.path.isdir(workspace):
        raise PermissionError("Configured admin workspace path does not exist")
    return workspace


def enforce_file_size_limit(size: int, limit: int, detail: str) -> None:
    if size > limit:
        raise ValueError(detail)


def backup_path_for(filepath: str) -> str:
    return f"{filepath}.bak"


async def mark_file_operation(user_id: str, path: str, status: str, backup_path: str | None = None) -> None:
    from xoai.db.mongo import get_db

    db = get_db()
    await db.file_operations.update_one(
        {"user_id": user_id, "path": path},
        {
            "$set": {
                "user_id": user_id,
                "path": path,
                "backup_path": backup_path,
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {"created_at": datetime.now(timezone.utc)},
        },
        upsert=True,
    )


async def atomic_write_bytes(user_id: str, filepath: str, payload: bytes) -> None:
    backup_path = backup_path_for(filepath)
    temp_path = f"{filepath}.tmp"
    await mark_file_operation(user_id, filepath, "in_progress", backup_path)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath):
        shutil.copy2(filepath, backup_path)

    with open(temp_path, "wb") as handle:
        handle.write(payload)
    os.replace(temp_path, filepath)

    if os.path.exists(backup_path):
        os.remove(backup_path)
    await mark_file_operation(user_id, filepath, "completed", backup_path)
    await untrack_storage_artifact(user_id, backup_path)


async def atomic_write_text(user_id: str, filepath: str, content: str) -> None:
    await atomic_write_bytes(user_id, filepath, content.encode("utf-8"))


async def atomic_replace_file(user_id: str, filepath: str, temp_path: str) -> None:
    backup_path = backup_path_for(filepath)
    await mark_file_operation(user_id, filepath, "in_progress", backup_path)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath):
        shutil.copy2(filepath, backup_path)
    os.replace(temp_path, filepath)
    if os.path.exists(backup_path):
        os.remove(backup_path)
    await mark_file_operation(user_id, filepath, "completed", backup_path)


def create_upload_session_path(user_id: str, upload_id: str) -> str:
    session_dir = os.path.join(get_user_upload_tmp(user_id), upload_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def upload_chunk_path(user_id: str, upload_id: str, chunk_index: int) -> str:
    session_dir = create_upload_session_path(user_id, upload_id)
    return os.path.join(session_dir, f"chunk_{chunk_index:08d}.part")


def merge_upload_chunks(user_id: str, upload_id: str, total_chunks: int, destination_path: str) -> tuple[int, str, str]:
    session_dir = create_upload_session_path(user_id, upload_id)
    temp_path = f"{destination_path}.uploading.{uuid.uuid4().hex}"
    hasher = hashlib.sha256()
    total_bytes = 0
    with open(temp_path, "wb") as out:
        for chunk_index in range(total_chunks):
            part_path = os.path.join(session_dir, f"chunk_{chunk_index:08d}.part")
            if not os.path.exists(part_path):
                raise FileNotFoundError(f"Missing upload chunk {chunk_index}")
            with open(part_path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    out.write(chunk)
                    hasher.update(chunk)
                    total_bytes += len(chunk)
    return total_bytes, hasher.hexdigest(), temp_path


def cleanup_upload_session_files(user_id: str, upload_id: str) -> None:
    session_dir = os.path.join(get_user_upload_tmp(user_id), upload_id)
    if os.path.isdir(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)


async def recover_in_progress_file_operations() -> int:
    from xoai.db.mongo import get_db

    db = get_db()
    ops = await db.file_operations.find({"status": "in_progress"}).to_list(500)
    recovered = 0
    for op in ops:
        path = op["path"]
        backup_path = op.get("backup_path") or backup_path_for(path)
        try:
            if os.path.exists(backup_path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                shutil.copy2(backup_path, path)
                os.remove(backup_path)
                recovered += 1
            await db.file_operations.update_one(
                {"_id": op["_id"]},
                {
                    "$set": {
                        "status": "recovered",
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
        except Exception:
            logger.exception("Failed to recover in-progress file operation", extra={"path": path})
            await db.file_operations.update_one(
                {"_id": op["_id"]},
                {
                    "$set": {
                        "status": "recovery_failed",
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
    return recovered


def calculate_dir_size(path: str) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total


async def check_quota(user_id: str, additional_bytes: int = 0, workspace: str = None) -> bool:
    """Check if a user's workspace is within quota."""
    from xoai.db.mongo import get_db
    from bson import ObjectId
    
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return False
        
    if user.get("role") == "admin" and ADMIN_QUOTA_BYPASS:
        return True
        
    limit = user.get("quota_limit_bytes", QUOTA_LIMIT_BYTES)

    if not workspace:
        workspace = get_user_workspace(user_id)
        
    if not os.path.exists(workspace):
        return True
    current = calculate_dir_size(workspace)
    return (current + additional_bytes) <= limit


def file_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
