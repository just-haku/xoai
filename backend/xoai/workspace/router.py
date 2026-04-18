"""Workspace file browser API."""

import base64
import mimetypes
import os
from html import escape
from pathlib import PurePath

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from xoai.auth.dependencies import get_current_user
from xoai.admin.service import get_setting
from xoai.workspace.service import (
    atomic_write_bytes,
    enforce_file_size_limit,
    ensure_not_workspace_root,
    get_admin_workspace,
    get_user_workspace,
    resolve_safe_path,
    check_quota,
)
from xoai.config import settings

router = APIRouter()


class SaveTextFilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=512)
    content: str = Field(max_length=5 * 1024 * 1024)


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
    try:
        ensure_not_workspace_root(path, workspace, operation)
    except PermissionError as exc:
        raise HTTPException(400, str(exc)) from exc

async def get_effective_workspace(user: dict) -> str | None:
    """Return the base workspace path. Returns None for normal user-isolated path."""
    if user.get("role") == "admin":
        try:
            setting = await get_setting("admin_workspace_path")
            if setting:
                if isinstance(setting, dict) and setting.get("path"):
                    return str(setting["path"])
                if isinstance(setting, str):
                    return setting
            return get_admin_workspace()
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
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
async def read_file(
    path: str,
    download: bool = False,
    base64_encode: bool = Query(False, alias="base64"),
    user: dict = Depends(get_current_user),
):
    """Read file content for preview."""
    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], path, workspace)
    if not os.path.isfile(safe_path):
        raise HTTPException(404, "File not found")

    if download:
        guessed_type = mimetypes.guess_type(safe_path)[0] or "application/octet-stream"
        return FileResponse(safe_path, filename=os.path.basename(safe_path), media_type=guessed_type)

    if base64_encode:
        with open(safe_path, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("ascii")
        return {"content": encoded}

    try:
        with open(safe_path, "r", encoding="utf-8", errors="ignore") as handle:
            return {"content": handle.read()}
    except Exception as exc:
        raise HTTPException(500, f"Error reading file: {exc}") from exc


@router.post("/files/save")
async def save_text_file(payload: SaveTextFilePayload, user: dict = Depends(get_current_user)):
    workspace = await get_effective_workspace(user)
    safe_path = _resolve_or_403(user["id"], payload.path, workspace)
    try:
        enforce_file_size_limit(len(payload.content.encode("utf-8")), settings.max_editor_bytes, "File exceeds editor size limit")
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    await atomic_write_bytes(user["id"], safe_path, payload.content.encode("utf-8"))
    return {"message": "Saved successfully"}


@router.post("/files/upload")
async def upload_file(
    path: str = "",
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a file to user's workspace (quota enforced)."""
    content = await file.read()
    workspace = await get_effective_workspace(user)
    try:
        enforce_file_size_limit(len(content), settings.max_upload_bytes, "Upload exceeds size limit")
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc

    if user.get("role") != "admin" and not await check_quota(user["id"], len(content), workspace):
        raise HTTPException(413, "Storage quota exceeded.")

    safe_dir = _resolve_or_403(user["id"], path, workspace)
    os.makedirs(safe_dir, exist_ok=True)
    safe_name = _safe_upload_filename(file.filename)
    dest = _resolve_or_403(user["id"], os.path.join(path, safe_name), workspace)

    await atomic_write_bytes(user["id"], dest, content)

    return {"message": "Uploaded", "path": os.path.join(path, safe_name)}


@router.delete("/files")
async def delete_file(path: str, user: dict = Depends(get_current_user)):
    """Delete a file from user's workspace."""
    workspace = await get_effective_workspace(user)
    effective_workspace = workspace or get_user_workspace(user["id"])
    safe_path = _resolve_or_403(user["id"], path, workspace)
    try:
        ensure_not_workspace_root(safe_path, effective_workspace, "delete")
    except PermissionError as exc:
        raise HTTPException(400, str(exc)) from exc
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
        enforce_file_size_limit(len(html_content.encode("utf-8")), settings.max_editor_bytes, "Document exceeds editor size limit")
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
                
        temp_bytes_path = f"{safe_path}.generated"
        doc.save(temp_bytes_path)
        with open(temp_bytes_path, "rb") as handle:
            payload = handle.read()
        os.remove(temp_bytes_path)
        await atomic_write_bytes(user["id"], safe_path, payload)
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
        enforce_file_size_limit(len(str(data).encode("utf-8")), settings.max_editor_bytes, "Spreadsheet exceeds editor size limit")
        if not data:
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(data)
        temp_bytes_path = f"{safe_path}.generated"
        df.to_excel(temp_bytes_path, index=False)
        with open(temp_bytes_path, "rb") as handle:
            payload = handle.read()
        os.remove(temp_bytes_path)
        await atomic_write_bytes(user["id"], safe_path, payload)
        return {"message": "Saved successfully"}
    except Exception as e:
        raise HTTPException(500, f"Error saving xlsx: {str(e)}")
