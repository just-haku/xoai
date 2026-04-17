"""FastAPI dependencies for authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from xoai.auth.service import decode_token
from xoai.db.mongo import get_db

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Extract and validate the current user from JWT."""
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    db = get_db()
    from bson import ObjectId

    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user["status"] != "approved":
        raise HTTPException(status_code=403, detail="Account not approved")

    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)
    return user


async def require_admin(user: dict = Depends(get_current_user)):
    """Require the current user to be an admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_current_user_ws(token: str):
    """Validate a token for WebSocket connections."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        db = get_db()
        from bson import ObjectId
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user or user["status"] != "approved":
            return None
        user["id"] = str(user.pop("_id"))
        user.pop("password_hash", None)
        return user
    except Exception:
        return None
