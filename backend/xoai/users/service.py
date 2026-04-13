"""User management service."""

import os

from bson import ObjectId

from xoai.config import settings
from xoai.db.mongo import get_db


QUOTA_LIMIT_BYTES = 15 * 1024 * 1024 * 1024  # 15GB


async def list_users(skip: int = 0, limit: int = 50):
    db = get_db()
    cursor = db.users.find({}, {"password_hash": 0}).skip(skip).limit(limit)
    users = []
    async for u in cursor:
        u["id"] = str(u.pop("_id"))
        users.append(u)
    return users


async def get_user(user_id: str):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if user:
        user["id"] = str(user.pop("_id"))
    return user


async def approve_user(user_id: str) -> bool:
    db = get_db()
    result = await db.users.update_one(
        {"_id": ObjectId(user_id), "status": "pending"},
        {"$set": {"status": "approved"}},
    )
    if result.modified_count:
        # Provision workspace + venv
        user_storage = os.path.join(settings.xoai_storage, "users", user_id)
        os.makedirs(os.path.join(user_storage, "workspace"), exist_ok=True)
        # venv will be provisioned lazily on first agent use
        return True
    return False


async def disable_user(user_id: str) -> bool:
    db = get_db()
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": "disabled"}},
    )
    return result.modified_count > 0


async def update_user_lang(user_id: str, lang: str):
    db = get_db()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"lang": lang}},
    )
