"""Filesystem tools — read, write, list with path jail + quota."""

import os

from xoai.config import settings
from xoai.workspace.service import (
    atomic_write_text,
    check_quota,
    enforce_file_size_limit,
    resolve_safe_path,
)


async def list_files(user_id: str, path: str = "") -> str:
    safe = resolve_safe_path(user_id, path)
    if not os.path.isdir(safe):
        return "Error: directory not found."
    return str(os.listdir(safe))


async def read_file(user_id: str, path: str) -> str:
    if not await check_quota(user_id):
        return "Error: storage quota exceeded. Access restricted."
    safe = resolve_safe_path(user_id, path)
    if not os.path.isfile(safe):
        return "Error: file not found."
    with open(safe, "r", errors="ignore") as f:
        return f.read()


async def write_file(user_id: str, path: str, content: str) -> str:
    encoded = content.encode()
    try:
        enforce_file_size_limit(len(encoded), settings.max_editor_bytes, "Error: file exceeds editor size limit.")
    except ValueError as exc:
        return str(exc)
    if not await check_quota(user_id, len(encoded)):
        return "Error: storage quota exceeded."
    safe = resolve_safe_path(user_id, path)
    os.makedirs(os.path.dirname(safe), exist_ok=True)
    await atomic_write_text(user_id, safe, content)
    return "OK"
