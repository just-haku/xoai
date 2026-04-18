"""Auth API routes: register, login, refresh, logout, verification, reset-password, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from typing import Annotated
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from xoai.auth.dependencies import get_current_user
from xoai.auth.service import (
    AuthError,
    consume_password_reset_token,
    create_access_token,
    create_password_reset_token,
    create_refresh_session,
    generate_numeric_code,
    hash_password,
    revoke_all_refresh_sessions,
    revoke_refresh_session,
    rotate_refresh_session,
    store_verification_code,
    verify_password,
)
from xoai.db.mongo import get_db
from xoai.jobs import job_manager
from xoai.metrics import metrics
from xoai.utils.rate_limit import build_client_key, rate_limiter

router = APIRouter()


def _slugify_name(name: str) -> str:
    return "_".join(name.strip().lower().split())


def _user_payload(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "username": user.get("username", ""),
        "name": user["name"],
        "role": user["role"],
        "lang": user.get("lang", "EN"),
        "avatar": user.get("avatar"),
    }


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=8)
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120, pattern=r"^[^$<>]{2,120}$")]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifier: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120, pattern=r"^[^$<>]{1,120}$")]
    password: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=16, max_length=4096)]


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str | None = None


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=16, max_length=4096)]
    password: str = Field(min_length=8)


@router.post("/register")
async def register(req: RegisterRequest, request: Request):
    rate_limiter.enforce(build_client_key(request, "auth.register"), 10, 60, "Too many registration attempts")
    db = get_db()
    username = _slugify_name(req.name)
    existing = await db.users.find_one({"$or": [{"email": req.email}, {"username": username}]})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already registered")

    user_doc = {
        "username": username,
        "email": req.email,
        "password_hash": hash_password(req.password),
        "name": req.name,
        "role": "user",
        "status": "pending",
        "email_verified": False,
        "quota_used_bytes": 0,
        "lang": "EN",
    }
    try:
        result = await db.users.insert_one(user_doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already registered") from exc

    code = generate_numeric_code()
    user_id = str(result.inserted_id)
    await store_verification_code(user_id=user_id, code_type="register_email", target=req.email, code=code)
    verify_link = f"{request.base_url}api/auth/verify-email?user_id={user_id}&code={code}"
    await job_manager.enqueue(
        "verification_email",
        {
            "email": req.email,
            "subject": "XOAI Verify Email",
            "code_or_link": verify_link,
        },
    )
    metrics.incr("auth.registered")
    return {"message": "Registration successful. Please verify your email.", "user_id": user_id}


@router.get("/verify-email")
async def verify_email(user_id: str, code: str, request: Request):
    rate_limiter.enforce(build_client_key(request, "auth.verify"), 20, 60, "Too many verification attempts")
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        await consume_verification_code(user_id=user_id, code_type="register_email", target=user["email"], code=code)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    await db.users.update_one({"_id": user["_id"]}, {"$set": {"email_verified": True}})
    metrics.incr("auth.email_verified")
    return {"message": "Email verified. Awaiting admin approval."}


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    rate_limiter.enforce(build_client_key(request, "auth.login"), 20, 60, "Too many login attempts")
    db = get_db()
    user = await db.users.find_one({"$or": [{"email": req.identifier}, {"username": req.identifier}]})
    if not user or not verify_password(req.password, user["password_hash"]):
        metrics.incr("auth.login_failed")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Email not verified")
    if user["status"] != "approved":
        raise HTTPException(status_code=403, detail="Account pending approval")

    user_id = str(user["_id"])
    session_id, refresh_token = await create_refresh_session(
        user_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    access_token = create_access_token(user_id, user["role"], session_id)
    metrics.incr("auth.login_success")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "session_id": session_id,
        "user": _user_payload(user),
    }


@router.post("/refresh")
async def refresh(req: RefreshRequest, request: Request):
    rate_limiter.enforce(build_client_key(request, "auth.refresh"), 30, 60, "Too many refresh attempts")
    try:
        rotated = await rotate_refresh_session(
            req.refresh_token,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    db = get_db()

    user = await db.users.find_one({"_id": ObjectId(rotated["user_id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "access_token": create_access_token(rotated["user_id"], user["role"], rotated["session_id"]),
        "refresh_token": rotated["refresh_token"],
        "session_id": rotated["session_id"],
        "user": _user_payload(user),
    }


@router.post("/logout")
async def logout(req: LogoutRequest, user: dict = Depends(get_current_user)):
    await revoke_refresh_session(req.session_id or user.get("session_id"))
    return {"message": "Logged out"}


@router.post("/logout-all")
async def logout_all(user: dict = Depends(get_current_user)):
    await revoke_all_refresh_sessions(user["id"])
    return {"message": "All sessions revoked"}


@router.post("/password-reset/request")
async def request_password_reset(req: PasswordResetRequest, request: Request):
    rate_limiter.enforce(build_client_key(request, "auth.password_reset"), 10, 60, "Too many password reset attempts")
    db = get_db()
    user = await db.users.find_one({"email": req.email})
    if user:
        token = await create_password_reset_token(str(user["_id"]), req.email)
        reset_link = f"{request.base_url}api/auth/password-reset/confirm?token={token}"
        await job_manager.enqueue(
            "verification_email",
            {
                "email": req.email,
                "subject": "XOAI Password Reset",
                "code_or_link": reset_link,
            },
        )
    return {"message": "If the account exists, a password reset link has been queued."}


@router.post("/password-reset/confirm")
async def confirm_password_reset(req: PasswordResetConfirmRequest):
    try:
        token_doc = await consume_password_reset_token(req.token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    db = get_db()

    await db.users.update_one(
        {"_id": ObjectId(token_doc["user_id"])},
        {"$set": {"password_hash": hash_password(req.password)}},
    )
    await revoke_all_refresh_sessions(token_doc["user_id"])
    return {"message": "Password updated"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
