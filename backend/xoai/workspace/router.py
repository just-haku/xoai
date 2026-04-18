"""Workspace file browser API."""

import base64
import hashlib
import mimetypes
import os
import uuid
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import PurePath

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from xoai.auth.dependencies import get_current_user
from xoai.admin.service import get_setting
from xoai.workspace.service import (
    atomic_write_bytes,
    atomic_replace_file,
    cleanup_upload_session_files,
    enforce_file_size_limit,
    ensure_not_workspace_root,
    get_admin_workspace,
    get_user_workspace,
    merge_upload_chunks,
    resolve_safe_path,
    check_quota,
    upload_chunk_path,
)
from xoai.config import settings
from xoai.storage_gc import track_storage_artifact, untrack_storage_artifact

router = APIRouter()


class SaveTextFilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=512)
    content: str = Field(max_length=5 * 1024 * 1024)


class UploadSessionInitPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(default="", max_length=512)
    filename: str = Field(min_length=1, max_length=255)
    total_size: int = Field(default=0, ge=0)
    total_chunks: int = Field(default=1, ge=1)
    mime_type: str | None = None


class UploadSessionCompletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha256: str | None = None


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
    workspace = await get_effective_workspace(user)
    safe_dir = _resolve_or_403(user["id"], path, workspace)
    os.makedirs(safe_dir, exist_ok=True)
    safe_name = _safe_upload_filename(file.filename)
    dest = _resolve_or_403(user["id"], os.path.join(path, safe_name), workspace)
    temp_path = f"{dest}.streaming.{uuid.uuid4().hex}"
    size = 0
    hasher = hashlib.sha256()
    with open(temp_path, "wb") as handle:
        while True:
            chunk = await file.read(settings.upload_chunk_bytes)
            if not chunk:
                break
            size += len(chunk)
            try:
                enforce_file_size_limit(size, settings.max_upload_bytes, "Upload exceeds size limit")
            except ValueError as exc:
                os.remove(temp_path)
                raise HTTPException(413, str(exc)) from exc
            hasher.update(chunk)
            handle.write(chunk)

    if user.get("role") != "admin" and not await check_quota(user["id"], size, workspace):
        os.remove(temp_path)
        raise HTTPException(413, "Storage quota exceeded.")
    await atomic_replace_file(user["id"], dest, temp_path)

    return {"message": "Uploaded", "path": os.path.join(path, safe_name), "sha256": hasher.hexdigest(), "size": size}


@router.post("/files/upload/init")
async def init_chunked_upload(payload: UploadSessionInitPayload, user: dict = Depends(get_current_user)):
    workspace = await get_effective_workspace(user)
    safe_dir = _resolve_or_403(user["id"], payload.path, workspace)
    os.makedirs(safe_dir, exist_ok=True)
    safe_name = _safe_upload_filename(payload.filename)
    upload_id = uuid.uuid4().hex
    upload_path = _resolve_or_403(user["id"], os.path.join(payload.path, safe_name), workspace)
    from xoai.db.mongo import get_db

    db = get_db()
    now = datetime.now(timezone.utc)
    await db.upload_sessions.insert_one(
        {
            "upload_id": upload_id,
            "user_id": user["id"],
            "path": payload.path,
            "filename": safe_name,
            "upload_path": upload_path,
            "chunk_size": settings.upload_chunk_bytes,
            "total_size": payload.total_size,
            "total_chunks": payload.total_chunks,
            "received_chunks": [],
            "received_bytes": 0,
            "status": "pending",
            "mime_type": payload.mime_type,
            "sha256": None,
            "expires_at": now + timedelta(hours=settings.upload_session_ttl_hours),
            "created_at": now,
            "updated_at": now,
        }
    )
    session_dir = os.path.dirname(upload_chunk_path(user["id"], upload_id, 0))
    await track_storage_artifact(
        user_id=user["id"],
        path=session_dir,
        artifact_type="upload_session",
        retention_class="upload_chunk",
    )
    return {"upload_id": upload_id, "chunk_size": settings.upload_chunk_bytes, "filename": safe_name, "total_chunks": payload.total_chunks}


@router.put("/files/upload/{upload_id}/chunk/{chunk_index}")
async def append_upload_chunk(
    upload_id: str,
    chunk_index: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    from xoai.db.mongo import get_db
    db = get_db()
    session = await db.upload_sessions.find_one({"upload_id": upload_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(404, "Upload session not found")
    if chunk_index < 0 or chunk_index >= int(session.get("total_chunks", 0) or 0):
        raise HTTPException(400, "Invalid chunk index")

    part_path = upload_chunk_path(user["id"], upload_id, chunk_index)
    size = 0
    with open(part_path, "wb") as handle:
        while True:
            chunk = await file.read(settings.upload_chunk_bytes)
            if not chunk:
                break
            size += len(chunk)
            handle.write(chunk)

    if user.get("role") != "admin" and not await check_quota(user["id"], size, await get_effective_workspace(user)):
        os.remove(part_path)
        raise HTTPException(413, "Storage quota exceeded.")

    received = sorted(set(list(session.get("received_chunks", [])) + [chunk_index]))
    await db.upload_sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "received_chunks": received,
                "received_bytes": int(session.get("received_bytes", 0)) + size,
                "updated_at": datetime.now(timezone.utc),
                "status": "uploading",
            }
        },
    )
    return {"upload_id": upload_id, "chunk_index": chunk_index, "size": size}


@router.post("/files/upload/{upload_id}/complete")
async def complete_chunked_upload(upload_id: str, payload: UploadSessionCompletePayload, user: dict = Depends(get_current_user)):
    from xoai.db.mongo import get_db
    db = get_db()
    session = await db.upload_sessions.find_one({"upload_id": upload_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(404, "Upload session not found")
    total_chunks = int(session.get("total_chunks", 0))
    received_chunks = list(session.get("received_chunks", []))
    if len(received_chunks) != total_chunks:
        raise HTTPException(409, "Upload session is incomplete")

    total_bytes, digest, temp_path = merge_upload_chunks(user["id"], upload_id, total_chunks, session["upload_path"])
    if payload.sha256 and payload.sha256 != digest:
        os.remove(temp_path)
        raise HTTPException(409, "Upload checksum mismatch")
    try:
        enforce_file_size_limit(total_bytes, settings.max_upload_bytes, "Upload exceeds size limit")
    except ValueError as exc:
        os.remove(temp_path)
        raise HTTPException(413, str(exc)) from exc

    await atomic_replace_file(user["id"], session["upload_path"], temp_path)
    cleanup_upload_session_files(user["id"], upload_id)
    await untrack_storage_artifact(user["id"], os.path.dirname(upload_chunk_path(user["id"], upload_id, 0)))
    await db.upload_sessions.update_one(
        {"_id": session["_id"]},
        {"$set": {"status": "completed", "sha256": digest, "updated_at": datetime.now(timezone.utc)}},
    )
    return {
        "message": "Uploaded",
        "path": os.path.join(session["path"], session["filename"]).strip("/"),
        "sha256": digest,
        "size": total_bytes,
    }


@router.delete("/files/upload/{upload_id}")
async def abort_chunked_upload(upload_id: str, user: dict = Depends(get_current_user)):
    from xoai.db.mongo import get_db
    from datetime import datetime, timezone

    db = get_db()
    session = await db.upload_sessions.find_one({"upload_id": upload_id, "user_id": user["id"]})
    if not session:
        raise HTTPException(404, "Upload session not found")
    cleanup_upload_session_files(user["id"], upload_id)
    await untrack_storage_artifact(user["id"], os.path.dirname(upload_chunk_path(user["id"], upload_id, 0)))
    await db.upload_sessions.update_one(
        {"_id": session["_id"]},
        {"$set": {"status": "aborted", "updated_at": datetime.now(timezone.utc)}},
    )
    return {"status": "aborted", "upload_id": upload_id}


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
