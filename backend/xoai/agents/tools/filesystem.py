"""Filesystem tools — read, write, list with path jail + quota."""

import os
from xoai.workspace.service import resolve_safe_path, check_quota


async def list_files(user_id: str, path: str = "") -> str:
    safe = resolve_safe_path(user_id, path)
    if not os.path.isdir(safe):
        return "Error: directory not found."
    return str(os.listdir(safe))


async def read_file(user_id: str, path: str) -> str:
    safe = resolve_safe_path(user_id, path)
    if not os.path.isfile(safe):
        return "Error: file not found."
    with open(safe, "r", errors="ignore") as f:
        return f.read()


async def write_file(user_id: str, path: str, content: str) -> str:
    if not check_quota(user_id, len(content.encode())):
        return "Error: storage quota exceeded (15GB limit)."
    safe = resolve_safe_path(user_id, path)
    os.makedirs(os.path.dirname(safe), exist_ok=True)
    with open(safe, "w", encoding="utf-8") as f:
        f.write(content)
    return "OK"
