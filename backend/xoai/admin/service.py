"""Admin settings service — CRUD for encrypted settings in MongoDB."""

from xoai.db.mongo import get_db
from xoai.auth.service import encrypt_value, decrypt_json, decrypt_value


async def get_setting(key: str) -> dict | None:
    db = get_db()
    doc = await db.settings.find_one({"key": key})
    if not doc:
        return None
    try:
        return decrypt_json(doc["value_encrypted"])
    except Exception:
        return {"raw": decrypt_value(doc["value_encrypted"])}


async def set_setting(key: str, value: dict):
    db = get_db()
    encrypted = encrypt_value(value)
    await db.settings.update_one(
        {"key": key},
        {"$set": {"key": key, "value_encrypted": encrypted}},
        upsert=True,
    )


async def delete_setting(key: str) -> bool:
    db = get_db()
    result = await db.settings.delete_one({"key": key})
    return result.deleted_count > 0


async def list_setting_keys() -> list[str]:
    db = get_db()
    cursor = db.settings.find({}, {"key": 1, "_id": 0})
    return [doc["key"] async for doc in cursor]
