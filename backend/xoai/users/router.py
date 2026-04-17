import random
import string
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File

from xoai.auth.dependencies import require_admin, get_current_user
from xoai.users import service
from pydantic import BaseModel

router = APIRouter()


def _user_object_id(user: dict) -> ObjectId:
    return ObjectId(user["id"])


def _object_id(value: str) -> ObjectId:
    return ObjectId(value)

class EmailCodeReq(BaseModel):
    email: str

class EmailUpdateReq(BaseModel):
    email: str
    code: str

class PasswordResetReq(BaseModel):
    password: str

class IntegrationsReq(BaseModel):
    discord: Optional[str] = ""
    telegram: Optional[str] = ""
    zalo: Optional[str] = ""

class ProfileUpdateReq(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None

class PasswordChangeReq(BaseModel):
    old_password: str
    new_password: str

@router.put("/profile")
async def update_profile(req: ProfileUpdateReq, user=Depends(get_current_user)):
    from xoai.db.mongo import db

    update_data = {}
    if req.name: update_data["name"] = req.name
    if req.bio: update_data["bio"] = req.bio
    if req.email: update_data["email"] = req.email
    
    if not update_data:
        return {"status": "no-op"}

    await db.users.update_one({"_id": _user_object_id(user)}, {"$set": update_data})
    return {"status": "ok"}

@router.post("/change-password")
async def change_password(req: PasswordChangeReq, user=Depends(get_current_user)):
    from xoai.auth.service import verify_password, hash_password
    from xoai.db.mongo import db
    
    # Get the user with password_hash
    user_doc = await db.users.find_one({"_id": _user_object_id(user)})
    if not verify_password(req.old_password, user_doc["password_hash"]):
        raise HTTPException(400, "Invalid old password")
    
    await db.users.update_one(
        {"_id": _user_object_id(user)},
        {"$set": {"password_hash": hash_password(req.new_password)}}
    )
    return {"status": "ok"}

@router.put("/integrations")
async def update_integrations(req: IntegrationsReq, user=Depends(get_current_user)):
    user_id = user["id"]
    from xoai.db.mongo import db
    from xoai.auth.service import encrypt_value
    from xoai.channels.manager import restart_bot_instance, stop_bot_instance

    for provider, token in [("discord", req.discord), ("telegram", req.telegram), ("zalo", req.zalo)]:
        if token and token.strip():
            await db.bot_instances.update_one(
                {"user_id": user_id, "platform": provider},
                {"$set": {"token_encrypted": encrypt_value(token), "status": "active"}},
                upsert=True
            )
            await restart_bot_instance(user_id, provider, token)
        elif token == "":
            await db.bot_instances.delete_one({"user_id": user_id, "platform": provider})
            await stop_bot_instance(user_id, provider)
            
    return {"status": "ok"}

class IntelligenceReq(BaseModel):
    provider: str
    key: str
    model: Optional[str] = None

class FetchModelsReq(BaseModel):
    provider: str
    key: str
    base_url: Optional[str] = None

@router.put("/intelligence")
async def update_intelligence(req: IntelligenceReq, user=Depends(get_current_user)):
    user_id = user["id"]
    from xoai.db.mongo import db
    from xoai.auth.service import encrypt_value

    # Update or insert personal API key
    await db.api_keys.update_one(
        {"user_id": user_id, "is_fallback": False},
        {
            "$set": {
                "provider": req.provider,
                "key_encrypted": encrypt_value(req.key),
                "model": req.model,
                "updated_at": datetime.now(timezone.utc)
            },
            "$setOnInsert": {
                "user_id": user_id,
                "is_fallback": False,
                "created_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    return {"status": "ok"}

@router.post("/agent/models")
async def fetch_agent_models(req: FetchModelsReq, _: Any = Depends(get_current_user)):
    """Fetch available models for a personal agent using unsaved keys."""
    from xoai.agents.llm_pool import get_provider
    try:
        provider = await get_provider({
            "provider": req.provider,
            "key": req.key,
            "base_url": req.base_url
        })
        models = await provider.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch models: {str(e)}")

@router.put("/work_chat")
async def update_work_chat(data: dict, user=Depends(get_current_user)):
    work_chat_id = data.get("work_chat_id")
    from xoai.db.mongo import db
    await db.users.update_one(
        {"_id": _user_object_id(user)},
        {"$set": {"active_work_chat_id": work_chat_id}}
    )
    return {"status": "ok"}

@router.get("/")
async def list_users(skip: int = 0, limit: int = 50, _=Depends(require_admin)):
    return await service.list_users(skip, limit)


@router.post("/{user_id}/approve")
async def approve_user(user_id: str, _=Depends(require_admin)):
    ok = await service.approve_user(user_id)
    if not ok:
        raise HTTPException(404, "User not found or not pending")
    return {"message": f"User {user_id} approved"}


@router.post("/{user_id}/disable")
async def disable_user(user_id: str, current_user=Depends(require_admin)):
    operator_id = current_user["id"]
    ok = await service.disable_user(user_id, operator_id)
    if not ok:
        raise HTTPException(
            status_code=400, 
            detail="Cannot disable self, other admins, or user not found"
        )
    return {"message": f"User {user_id} disabled"}

@router.post("/email-verification-code")
async def send_email_code(req: EmailCodeReq, user=Depends(get_current_user)):
    from xoai.auth.service import send_verification_email
    from xoai.db.mongo import db
    
    code = ''.join(random.choices(string.digits, k=6))

    await db.verification_codes.update_one(
        {"user_id": user["id"], "type": "email_change"},
        {"$set": {"code": code, "target_email": req.email, "created_at": datetime.now(timezone.utc)}},
        upsert=True
    )

    success = await send_verification_email(req.email, code)
    if not success:
        raise HTTPException(500, "Failed to send email. Ensure Admin has configured SMTP From address.")
    
    return {"status": "ok"}

@router.put("/update-email")
async def update_email(req: EmailUpdateReq, user=Depends(get_current_user)):
    from xoai.db.mongo import db
    
    verify_doc = await db.verification_codes.find_one({
        "user_id": user["id"],
        "type": "email_change",
        "code": req.code,
        "target_email": req.email
    })
    
    if not verify_doc:
        raise HTTPException(400, "Invalid or expired verification code")
    
    # Update user email
    await db.users.update_one({"_id": _user_object_id(user)}, {"$set": {"email": req.email}})
    # Clean up code
    await db.verification_codes.delete_one({"_id": verify_doc["_id"]})
    
    return {"status": "ok"}

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), user=Depends(get_current_user)):
    # Simple local storage for demo
    # In production use S3 or similar
    upload_dir = Path("./static/avatars")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_ext = Path(file.filename).suffix
    file_path = upload_dir / f"{user['id']}{file_ext}"
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    url = f"/api/static/avatars/{user['id']}{file_ext}"
    from xoai.db.mongo import db
    await db.users.update_one({"_id": _user_object_id(user)}, {"$set": {"avatar": url}})
    
    return {"url": url}

@router.post("/{user_id}/reset-password")
async def reset_password(user_id: str, req: PasswordResetReq, _=Depends(require_admin)):
    from xoai.auth.service import hash_password
    from xoai.db.mongo import db
    
    await db.users.update_one(
        {"_id": _object_id(user_id)},
        {"$set": {"password_hash": hash_password(req.password)}}
    )
    return {"status": "ok"}
