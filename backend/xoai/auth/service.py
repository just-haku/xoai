"""Auth service: password hashing, JWT tokens, verification codes, and refresh sessions."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import aiosmtplib
import bcrypt
import jwt
from cryptography.fernet import Fernet
from email.message import EmailMessage
from jwt import ExpiredSignatureError, InvalidTokenError

from xoai.config import settings
from xoai.metrics import metrics

logger = logging.getLogger("xoai.auth")

# Derive a Fernet key from SECRET_KEY.
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
_fernet = Fernet(_fernet_key)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
PROXY_ACCESS_TOKEN_EXPIRE_MINUTES = 10
PROXY_HANDOFF_EXPIRE_MINUTES = 2
EMAIL_VERIFICATION_EXPIRE_MINUTES = 15
PASSWORD_RESET_EXPIRE_MINUTES = 30
MAX_VERIFICATION_ATTEMPTS = 5


class AuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 401):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def _encode_token(payload: dict) -> str:
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def create_access_token(
    user_id: str,
    role: str,
    session_id: str,
    *,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
    extra_claims: dict | None = None,
) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "session_id": session_id,
        "exp": utcnow() + timedelta(minutes=expires_minutes),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return _encode_token(payload)


def create_refresh_token(user_id: str, session_id: str) -> str:
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "exp": utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
        "jti": secrets.token_urlsafe(24),
    }
    return _encode_token(payload)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        metrics.incr("auth.token_expired")
        raise AuthError("token_expired", "Token has expired") from exc
    except InvalidTokenError as exc:
        metrics.incr("auth.token_invalid")
        raise AuthError("token_invalid", "Invalid token") from exc

    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise AuthError("token_type_invalid", "Invalid token type")
    return payload


def hash_token_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def generate_numeric_code(length: int = 6) -> str:
    alphabet = "0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def create_refresh_session(user_id: str, *, ip: str | None = None, user_agent: str | None = None) -> tuple[str, str]:
    from xoai.db.mongo import get_db

    db = get_db()
    session_id = str(uuid.uuid4())
    refresh_token = create_refresh_token(user_id, session_id)
    now = utcnow()
    await db.refresh_sessions.insert_one(
        {
            "session_id": session_id,
            "user_id": user_id,
            "token_hash": hash_token_value(refresh_token),
            "expires_at": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "revoked_at": None,
            "created_at": now,
            "last_used_at": now,
            "user_agent": user_agent,
            "ip": ip,
        }
    )
    return session_id, refresh_token


async def create_proxy_handoff(
    user_id: str,
    role: str,
    proxy_by: str,
    *,
    expires_minutes: int = PROXY_HANDOFF_EXPIRE_MINUTES,
) -> dict:
    from xoai.db.mongo import get_db

    db = get_db()
    handoff_token = secrets.token_urlsafe(32)
    session_id = str(uuid.uuid4())
    now = utcnow()
    expires_at = now + timedelta(minutes=expires_minutes)
    await db.proxy_handoffs.insert_one(
        {
            "user_id": user_id,
            "role": role,
            "proxy_by": proxy_by,
            "session_id": session_id,
            "token_hash": hash_token_value(handoff_token),
            "consumed_at": None,
            "created_at": now,
            "expires_at": expires_at,
        }
    )
    return {
        "handoff_token": handoff_token,
        "session_id": session_id,
        "expires_at": expires_at,
    }


async def consume_proxy_handoff(handoff_token: str) -> dict:
    from xoai.db.mongo import get_db

    db = get_db()
    token_hash = hash_token_value(handoff_token)
    now = utcnow()
    collection = db.proxy_handoffs
    if hasattr(collection, "find_one_and_update"):
        from pymongo import ReturnDocument

        doc = await collection.find_one_and_update(
            {
                "token_hash": token_hash,
                "consumed_at": None,
                "expires_at": {"$gt": now},
            },
            {"$set": {"consumed_at": now}},
            return_document=ReturnDocument.AFTER,
        )
    else:
        doc = await collection.find_one({"token_hash": token_hash})
        if doc and not doc.get("consumed_at") and doc.get("expires_at", now) > now:
            await collection.update_one({"_id": doc["_id"]}, {"$set": {"consumed_at": now}})
            doc["consumed_at"] = now
        else:
            doc = None
    if not doc:
        raise AuthError("proxy_handoff_invalid", "Invalid or expired proxy handoff token", 401)
    return doc


async def rotate_refresh_session(refresh_token: str, *, ip: str | None = None, user_agent: str | None = None) -> dict:
    from xoai.db.mongo import get_db

    payload = decode_token(refresh_token, expected_type="refresh")
    db = get_db()
    session = await db.refresh_sessions.find_one({"session_id": payload["session_id"]})
    if not session:
        raise AuthError("session_not_found", "Refresh session not found")
    if session.get("revoked_at"):
        raise AuthError("session_revoked", "Refresh session has been revoked")
    if session.get("token_hash") != hash_token_value(refresh_token):
        raise AuthError("refresh_token_mismatch", "Refresh token is no longer valid")

    new_refresh_token = create_refresh_token(payload["sub"], payload["session_id"])
    now = utcnow()
    await db.refresh_sessions.update_one(
        {"session_id": payload["session_id"]},
        {
            "$set": {
                "token_hash": hash_token_value(new_refresh_token),
                "last_used_at": now,
                "user_agent": user_agent or session.get("user_agent"),
                "ip": ip or session.get("ip"),
            }
        },
    )
    metrics.incr("auth.refresh_rotated")
    return {
        "user_id": payload["sub"],
        "session_id": payload["session_id"],
        "refresh_token": new_refresh_token,
    }


async def revoke_refresh_session(session_id: str) -> None:
    from xoai.db.mongo import get_db

    db = get_db()
    await db.refresh_sessions.update_one(
        {"session_id": session_id, "revoked_at": None},
        {"$set": {"revoked_at": utcnow()}},
    )


async def revoke_all_refresh_sessions(user_id: str) -> None:
    from xoai.db.mongo import get_db

    db = get_db()
    await db.refresh_sessions.update_many(
        {"user_id": user_id, "revoked_at": None},
        {"$set": {"revoked_at": utcnow()}},
    )


async def store_verification_code(
    *,
    user_id: str,
    code_type: str,
    target: str,
    code: str,
    expires_minutes: int = EMAIL_VERIFICATION_EXPIRE_MINUTES,
) -> None:
    from xoai.db.mongo import get_db

    db = get_db()
    now = utcnow()
    await db.verification_codes.update_one(
        {"user_id": user_id, "type": code_type},
        {
            "$set": {
                "target": target,
                "code_hash": hash_token_value(code),
                "attempts": 0,
                "expires_at": now + timedelta(minutes=expires_minutes),
                "updated_at": now,
                "created_at": now,
            }
        },
        upsert=True,
    )


async def consume_verification_code(*, user_id: str, code_type: str, target: str, code: str) -> None:
    from xoai.db.mongo import get_db

    db = get_db()
    doc = await db.verification_codes.find_one({"user_id": user_id, "type": code_type})
    if not doc or doc.get("target") != target:
        raise AuthError("verification_invalid", "Invalid or expired verification code", 400)
    if doc.get("expires_at") and doc["expires_at"] < utcnow():
        raise AuthError("verification_expired", "Verification code expired", 400)
    if int(doc.get("attempts", 0)) >= MAX_VERIFICATION_ATTEMPTS:
        raise AuthError("verification_attempts_exceeded", "Verification code attempt limit exceeded", 429)
    if doc.get("code_hash") != hash_token_value(code):
        await db.verification_codes.update_one({"_id": doc["_id"]}, {"$inc": {"attempts": 1}})
        raise AuthError("verification_invalid", "Invalid or expired verification code", 400)
    await db.verification_codes.delete_one({"_id": doc["_id"]})


async def create_password_reset_token(user_id: str, email: str) -> str:
    from xoai.db.mongo import get_db

    db = get_db()
    raw_token = secrets.token_urlsafe(32)
    now = utcnow()
    await db.password_reset_tokens.insert_one(
        {
            "user_id": user_id,
            "email": email,
            "token_hash": hash_token_value(raw_token),
            "expires_at": now + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES),
            "used_at": None,
            "created_at": now,
        }
    )
    return raw_token


async def consume_password_reset_token(token: str) -> dict:
    from xoai.db.mongo import get_db

    db = get_db()
    doc = await db.password_reset_tokens.find_one({"token_hash": hash_token_value(token)})
    if not doc or doc.get("used_at"):
        raise AuthError("password_reset_invalid", "Invalid password reset token", 400)
    if doc["expires_at"] < utcnow():
        raise AuthError("password_reset_expired", "Password reset token expired", 400)
    await db.password_reset_tokens.update_one({"_id": doc["_id"]}, {"$set": {"used_at": utcnow()}})
    return doc


def encrypt_value(value: dict | str) -> str:
    raw = json.dumps(value) if isinstance(value, dict) else value
    return _fernet.encrypt(raw.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()


def decrypt_json(encrypted: str) -> dict:
    return json.loads(decrypt_value(encrypted))


async def send_verification_email(to_email: str, code_or_link: str, *, subject: str = "XOAI Verification") -> bool:
    from xoai.db.mongo import db

    smtp_setting = await db.settings.find_one({"key": "smtp"})
    if not smtp_setting:
        logger.warning("SMTP settings not configured; skipping email send")
        return False

    admin_user = await db.users.find_one({"role": "admin"})
    admin_email = admin_user.get("email") if admin_user else None
    if not admin_email:
        logger.warning("Admin email not configured; skipping email send")
        return False

    try:
        settings_data = decrypt_json(smtp_setting["value_encrypted"])
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = admin_email
        msg["To"] = to_email
        if code_or_link.startswith(("http://", "https://")):
            msg.set_content(
                "Open this link to continue:\n\n"
                f"{code_or_link}\n\n"
                "If you did not request this, ignore this message."
            )
        else:
            msg.set_content(
                f"Your XOAI code is: {code_or_link}\n\nThis code expires in {EMAIL_VERIFICATION_EXPIRE_MINUTES} minutes."
            )

        await aiosmtplib.send(
            msg,
            hostname=settings_data.get("host", "smtp.gmail.com"),
            port=int(settings_data.get("port", 587)),
            username=settings_data.get("sender_email"),
            password=settings_data.get("password"),
            start_tls=True,
        )
        metrics.incr("auth.email_sent")
        return True
    except Exception as exc:
        logger.exception("SMTP send failed", extra={"email": to_email})
        metrics.incr("auth.email_failed")
        return False
