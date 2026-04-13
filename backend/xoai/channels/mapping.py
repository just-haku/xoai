"""Channel User Mapping — Linking external IDs (Zalo, Discord) to internal users."""

import logging
from xoai.db.mongo import get_db

logger = logging.getLogger("xoai.channels.mapping")


async def get_user_by_channel_id(channel: str, external_id: str) -> dict | None:
    """Find an internal user by an external channel ID (e.g. Zalo chat_id)."""
    db = get_db()
    # Mapping is stored in users.channel_mappings = {"zalo": "123", "discord": "456"}
    user = await db.users.find_one({f"channel_mappings.{channel}": external_id})
    return user


async def link_user_to_channel(user_id: str, channel: str, external_id: str):
    """Link an existing user to an external channel ID."""
    from bson import ObjectId
    db = get_db()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {f"channel_mappings.{channel}": external_id}}
    )
    logger.info(f"Linked user {user_id} to {channel}:{external_id}")
