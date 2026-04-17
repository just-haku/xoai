"""Auth API routes: register, login, verify-email, me."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from xoai.db.mongo import get_db
from xoai.auth.service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    decode_token,
)
from xoai.auth.dependencies import get_current_user

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    identifier: str  # username or email
    password: str


@router.post("/register")
async def register(req: RegisterRequest):
    db = get_db()
    existing = await db.users.find_one({
        "$or": [{"email": req.email}, {"username": req.name.lower().replace(" ", "_")}]
    })
    if existing:
        raise HTTPException(400, "User already registered")

    user_doc = {
        "username": req.name.lower().replace(" ", "_"),
        "email": req.email,
        "password_hash": hash_password(req.password),
        "name": req.name,
        "role": "user",
        "status": "pending",
        "email_verified": False,
        "quota_used_bytes": 0,
        "lang": "EN",
    }
    result = await db.users.insert_one(user_doc)
    token = create_email_verification_token(req.email)

    # Trigger SMTP verification email
    from xoai.auth.service import send_verification_email
    import asyncio
    asyncio.create_task(send_verification_email(req.email, token))

    return {
        "message": "Registration successful. Please verify your email.",
        "user_id": str(result.inserted_id),
    }


@router.get("/verify-email")
async def verify_email(token: str):
    try:
        payload = decode_token(token)
        if payload.get("type") != "email_verify":
            raise HTTPException(400, "Invalid token type")
    except Exception:
        raise HTTPException(400, "Invalid or expired verification token")

    db = get_db()
    result = await db.users.update_one(
        {"email": payload["email"]},
        {"$set": {"email_verified": True}},
    )
    if result.modified_count == 0:
        raise HTTPException(404, "User not found")

    return {"message": "Email verified. Awaiting admin approval."}


@router.post("/login")
async def login(req: LoginRequest):
    db = get_db()
    user = await db.users.find_one({
        "$or": [{"email": req.identifier}, {"username": req.identifier}]
    })
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    if not user.get("email_verified"):
        raise HTTPException(403, "Email not verified")
    if user["status"] != "approved":
        raise HTTPException(403, "Account pending approval")

    user_id = str(user["_id"])
    return {
        "access_token": create_access_token(user_id, user["role"]),
        "refresh_token": create_refresh_token(user_id),
        "user": {
            "id": user_id,
            "email": user["email"],
            "username": user.get("username", ""),
            "name": user["name"],
            "role": user["role"],
            "lang": user["lang"],
        },
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
