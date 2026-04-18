from pathlib import Path
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from fastapi.responses import FileResponse
from pymongo.errors import DuplicateKeyError

from xoai.auth.dependencies import require_admin, get_current_user
from xoai.auth.service import (
    AuthError,
    create_password_reset_token,
    generate_numeric_code,
    hash_password,
    revoke_all_refresh_sessions,
    store_verification_code,
    consume_verification_code,
)
from xoai.config import settings
from xoai.jobs import job_manager
from xoai.utils.rate_limit import build_client_key, rate_limiter
from xoai.users import service
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from typing import Annotated

router = APIRouter()

SafeName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=r"^[^$<>]{1,120}$")]
SafeBio = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500, pattern=r"^[^$<>]{0,500}$")]
SafeToken = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4096, pattern=r"^[^\x00]{1,4096}$")]
SafeProvider = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=32, pattern=r"^[a-zA-Z0-9._-]+$")]
SafeModel = Annotated[str, StringConstraints(strip_whitespace=True, max_length=128, pattern=r"^[a-zA-Z0-9._:/-]*$")]
SafeWorkChatId = Annotated[str, StringConstraints(strip_whitespace=True, max_length=128, pattern=r"^[a-zA-Z0-9._:-]*$")]


def _user_object_id(user: dict) -> ObjectId:
    return ObjectId(user["id"])


def _object_id(value: str) -> ObjectId:
    return ObjectId(value)

class EmailCodeReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr

class EmailUpdateReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=4, max_length=12, pattern=r"^[0-9A-Za-z_-]+$")]

class PasswordResetReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=8)

class IntegrationsReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    discord: Optional[SafeToken] = ""
    telegram: Optional[SafeToken] = ""
    zalo: Optional[SafeToken] = ""

class ProfileUpdateReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[SafeName] = None
    bio: Optional[SafeBio] = None
    email: Optional[EmailStr] = None

class PasswordChangeReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    old_password: str
    new_password: str = Field(min_length=8)


class WorkChatUpdateReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_chat_id: SafeWorkChatId | None = None

@router.put("/profile")
async def update_profile(req: ProfileUpdateReq, user=Depends(get_current_user)):
    from xoai.db.mongo import db

    update_data = {}
    if req.name: update_data["name"] = req.name
    if req.bio: update_data["bio"] = req.bio
    if req.email: update_data["email"] = req.email
    
    if not update_data:
        return {"status": "no-op"}

    try:
        await db.users.update_one({"_id": _user_object_id(user)}, {"$set": update_data})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Email already in use") from exc
    return {"status": "ok"}

@router.post("/change-password")
async def change_password(req: PasswordChangeReq, user=Depends(get_current_user)):
    from xoai.auth.service import verify_password
    from xoai.db.mongo import db
    
    # Get the user with password_hash
    user_doc = await db.users.find_one({"_id": _user_object_id(user)})
    if not verify_password(req.old_password, user_doc["password_hash"]):
        raise HTTPException(400, "Invalid old password")
    
    await db.users.update_one(
        {"_id": _user_object_id(user)},
        {"$set": {"password_hash": hash_password(req.new_password)}}
    )
    await revoke_all_refresh_sessions(user["id"])
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
    model_config = ConfigDict(extra="forbid")
    provider: SafeProvider
    key: SafeToken
    model: Optional[SafeModel] = None

class FetchModelsReq(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: SafeProvider
    key: SafeToken
    base_url: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]] = None

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
async def update_work_chat(data: WorkChatUpdateReq, user=Depends(get_current_user)):
    from xoai.db.mongo import db
    await db.users.update_one(
        {"_id": _user_object_id(user)},
        {"$set": {"active_work_chat_id": data.work_chat_id}}
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
async def send_email_code(req: EmailCodeReq, request: Request, user=Depends(get_current_user)):
    from xoai.db.mongo import db

    rate_limiter.enforce(build_client_key(request, "users.email_change", user["id"]), 10, 60, "Too many email verification attempts")
    existing = await db.users.find_one({"email": req.email, "_id": {"$ne": _user_object_id(user)}})
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")

    code = generate_numeric_code()
    await store_verification_code(user_id=user["id"], code_type="email_change", target=req.email, code=code)
    await job_manager.enqueue(
        "verification_email",
        {
            "email": req.email,
            "subject": "XOAI Confirm Email Change",
            "code_or_link": code,
        },
    )
    return {"status": "ok"}

@router.put("/update-email")
async def update_email(req: EmailUpdateReq, user=Depends(get_current_user)):
    from xoai.db.mongo import db

    try:
        await consume_verification_code(user_id=user["id"], code_type="email_change", target=req.email, code=req.code)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    try:
        await db.users.update_one({"_id": _user_object_id(user)}, {"$set": {"email": req.email}})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Email already in use") from exc
    return {"status": "ok"}

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), user=Depends(get_current_user)):
    allowed_types = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported avatar type")

    data = await file.read()
    if len(data) > settings.max_avatar_bytes:
        raise HTTPException(status_code=413, detail="Avatar exceeds size limit")

    upload_dir = Path(settings.xoai_storage) / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_ext = allowed_types[file.content_type]
    file_path = upload_dir / f"{user['id']}{file_ext}"

    with file_path.open("wb") as buffer:
        buffer.write(data)

    url = f"/api/users/avatar/{user['id']}{file_ext}"
    from xoai.db.mongo import db
    await db.users.update_one({"_id": _user_object_id(user)}, {"$set": {"avatar": url}})

    return {"url": url}


@router.get("/avatar/{filename}")
async def get_avatar(filename: str):
    avatar_path = Path(settings.xoai_storage) / "avatars" / Path(filename).name
    if not avatar_path.is_file():
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(avatar_path)

@router.post("/{user_id}/reset-password")
async def reset_password(user_id: str, req: PasswordResetReq, _=Depends(require_admin)):
    from xoai.db.mongo import db

    await db.users.update_one(
        {"_id": _object_id(user_id)},
        {"$set": {"password_hash": hash_password(req.password)}}
    )
    return {"status": "ok"}


@router.post("/{user_id}/issue-password-reset")
async def issue_password_reset(user_id: str, _=Depends(require_admin)):
    from xoai.db.mongo import db

    user_doc = await db.users.find_one({"_id": _object_id(user_id)})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    token = await create_password_reset_token(user_id, user_doc["email"])
    await job_manager.enqueue(
        "verification_email",
        {
            "email": user_doc["email"],
            "subject": "XOAI Password Reset",
            "code_or_link": f"{settings.public_base_url.rstrip('/')}/api/auth/password-reset/confirm?token={token}",
        },
    )
    return {"status": "ok"}
