"""Workspace file browser API."""

import os

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse

from xoai.auth.dependencies import get_current_user
from xoai.workspace.service import (
    get_user_workspace,
    resolve_safe_path,
    check_quota,
)

router = APIRouter()


@router.get("/files")
async def list_files(path: str = "", user: dict = Depends(get_current_user)):
    """List files in user's workspace directory."""
    safe_path = resolve_safe_path(user["id"], path)
    if not os.path.isdir(safe_path):
        raise HTTPException(404, "Directory not found")

    entries = []
    for name in sorted(os.listdir(safe_path)):
        full = os.path.join(safe_path, name)
        entries.append({
            "name": name,
            "is_dir": os.path.isdir(full),
            "size": os.path.getsize(full) if os.path.isfile(full) else 0,
        })
    return entries


@router.get("/files/download")
async def download_file(path: str, user: dict = Depends(get_current_user)):
    """Download a file from user's workspace."""
    safe_path = resolve_safe_path(user["id"], path)
    if not os.path.isfile(safe_path):
        raise HTTPException(404, "File not found")
    return FileResponse(safe_path, filename=os.path.basename(safe_path))


@router.post("/files/upload")
async def upload_file(
    path: str = "",
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a file to user's workspace (quota enforced)."""
    content = await file.read()

    if user.get("role") != "admin" and not check_quota(user["id"], len(content)):
        raise HTTPException(413, "Storage quota exceeded (15GB limit)")

    safe_dir = resolve_safe_path(user["id"], path)
    os.makedirs(safe_dir, exist_ok=True)
    dest = os.path.join(safe_dir, file.filename)

    with open(dest, "wb") as f:
        f.write(content)

    return {"message": "Uploaded", "path": os.path.join(path, file.filename)}


@router.delete("/files")
async def delete_file(path: str, user: dict = Depends(get_current_user)):
    """Delete a file from user's workspace."""
    safe_path = resolve_safe_path(user["id"], path)
    if not os.path.exists(safe_path):
        raise HTTPException(404, "File not found")

    if os.path.isdir(safe_path):
        import shutil
        shutil.rmtree(safe_path)
    else:
        os.remove(safe_path)

    return {"message": "Deleted"}
