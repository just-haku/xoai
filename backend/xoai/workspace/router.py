"""Workspace file browser API."""

import os
from html import escape
from pathlib import PurePath

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse

from xoai.auth.dependencies import get_current_user
from xoai.admin.service import get_setting
from xoai.workspace.service import (
    get_user_workspace,
    resolve_safe_path,
    check_quota,
)

router = APIRouter()


def _resolve_or_403(user_id: str, path: str, workspace: str | None = None) -> str:
    try:
        return resolve_safe_path(user_id, path, workspace)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


def _safe_upload_filename(filename: str | None) -> str:
    safe_name = PurePath(filename or "").name
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(400, "Invalid upload filename")
    return safe_name


def _ensure_not_workspace_root(path: str, workspace: str, operation: str) -> None:
    if os.path.abspath(path) == os.path.abspath(workspace):
        raise HTTPException(400, f"Refusing to {operation} the workspace root")


async def get_effective_workspace(user: dict) -> str | None:
    """Return the base workspace path. Returns None for normal user-isolated path."""
    if user.get("role") == "admin":
        setting = await get_setting("admin_workspace_path")
        if setting:
            # Setting might be {"path": "/..."} or just a string depending on how it's stored
            if isinstance(setting, dict):
                return setting.get("path") or "/"
            return str(setting)
        return "/"
    return None


@router.get("/files")
async def list_files(path: str = "", user: dict = Depends(get_current_user)):
    """List files in user's workspace directory."""
    if user.get("role") != "admin" and not await check_quota(user["id"]):
        raise HTTPException(413, "Storage quota exceeded. Access restricted.")
        
    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], path, workspace)
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
    if user.get("role") != "admin" and not await check_quota(user["id"]):
        raise HTTPException(413, "Storage quota exceeded. Access restricted.")

    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], path, workspace)
    if not os.path.isfile(safe_path):
        raise HTTPException(404, "File not found")
    return FileResponse(safe_path, filename=os.path.basename(safe_path))


@router.get("/files/read")
async def read_file(path: str, user: dict = Depends(get_current_user)):
    """Read file content for preview."""
    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], path, workspace)
    if not os.path.isfile(safe_path):
        raise HTTPException(404, "File not found")
    
    # Return as plain text for the preview modal
    return FileResponse(safe_path, media_type="text/plain")


@router.post("/files/upload")
async def upload_file(
    path: str = "",
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a file to user's workspace (quota enforced)."""
    content = await file.read()
    workspace = await get_effective_workspace(user)

    if user.get("role") != "admin" and not await check_quota(user["id"], len(content), workspace):
        raise HTTPException(413, "Storage quota exceeded.")

    safe_dir = _resolve_or_403(user["id"], path, workspace)
    os.makedirs(safe_dir, exist_ok=True)
    safe_name = _safe_upload_filename(file.filename)
    dest = _resolve_or_403(user["id"], os.path.join(path, safe_name), workspace)

    with open(dest, "wb") as f:
        f.write(content)

    return {"message": "Uploaded", "path": os.path.join(path, safe_name)}


@router.delete("/files")
async def delete_file(path: str, user: dict = Depends(get_current_user)):
    """Delete a file from user's workspace."""
    workspace = await get_effective_workspace(user)
    effective_workspace = workspace or get_user_workspace(user["id"])
    safe_path = _resolve_or_403(user["id"], path, workspace)
    _ensure_not_workspace_root(safe_path, effective_workspace, "delete")
    if not os.path.exists(safe_path):
        raise HTTPException(404, "File not found")

    if os.path.isdir(safe_path):
        import shutil
        shutil.rmtree(safe_path)
    else:
        os.remove(safe_path)

    return {"message": "Deleted"}


@router.get("/files/convert/docx")
async def convert_docx(path: str, user: dict = Depends(get_current_user)):
    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], path, workspace)
    if not os.path.isfile(safe_path):
        raise HTTPException(404, "File not found")
    
    try:
        from docx import Document
        doc = Document(safe_path)
        # Create a simple HTML-like structure from document blocks
        html_blocks = []
        for p in doc.paragraphs:
            if p.text.strip():
                html_blocks.append(f"<p>{escape(p.text)}</p>")
        return {"content": "".join(html_blocks)}
    except Exception as e:
        raise HTTPException(500, f"Error processing docx: {str(e)}")


@router.post("/files/save/docx")
async def save_docx(
    path: str,
    payload: dict,
    user: dict = Depends(get_current_user)
):
    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], path, workspace)
    
    try:
        html_content = payload.get("content", "")
        # Basic rebuild from HTML-like string to docx
        from docx import Document
        import re
        doc = Document()
        
        # Remove tags and recreate paragraphs
        # This is a basic implementation, can completely use beautifulsoup or markdown conversion later
        raw_text = re.sub(r'</?(p|div|h[1-6]|span|br|b|i)[^>]*>', '\n', html_content)
        for line in raw_text.split('\n'):
            line = line.strip()
            if line:
                doc.add_paragraph(line)
                
        doc.save(safe_path)
        return {"message": "Saved successfully"}
    except Exception as e:
        raise HTTPException(500, f"Error saving docx: {str(e)}")


@router.get("/files/convert/xlsx")
async def convert_xlsx(path: str, user: dict = Depends(get_current_user)):
    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], path, workspace)
    if not os.path.isfile(safe_path):
        raise HTTPException(404, "File not found")
        
    try:
        import pandas as pd
        df = pd.read_excel(safe_path)
        # Handle NA and dates for JSON serialization
        df = df.fillna("")
        return {"content": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(500, f"Error processing xlsx: {str(e)}")


@router.post("/files/save/xlsx")
async def save_xlsx(
    path: str,
    payload: dict,
    user: dict = Depends(get_current_user)
):
    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], path, workspace)
    
    try:
        import pandas as pd
        data = payload.get("content", [])
        if not data:
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(data)
        df.to_excel(safe_path, index=False)
        return {"message": "Saved successfully"}
    except Exception as e:
        raise HTTPException(500, f"Error saving xlsx: {str(e)}")
