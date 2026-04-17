"""Conversation memory + compression."""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("xoai.agents.memory")


async def get_conversation_messages(conversation_id: str, limit: int = 50) -> list:
    """Fetch recent messages for a conversation."""
    from xoai.db.mongo import get_db
    db = get_db()
    cursor = db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    docs.reverse()
    messages = []
    for doc in docs:
        msg = {
            "role": doc["role"],
            "content": doc.get("content", ""),
        }
        if doc.get("tool_calls"):
            msg["tool_calls"] = doc["tool_calls"]
        messages.append(msg)
    return messages


async def save_message(conversation_id: str, role: str, content: str, **kwargs):
    """Save a message to the conversation."""
    from xoai.db.mongo import get_db
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "tool_calls": kwargs.get("tool_calls", []),
        "channel_metadata": kwargs.get("channel_metadata", {}),
        "created_at": now,
    }
    await db.messages.insert_one(doc)

    user_id = kwargs.get("user_id")
    if user_id:
        await db.conversations.update_one(
            {"chat_id": conversation_id, "user_id": user_id},
            {
                "$setOnInsert": {
                    "chat_id": conversation_id,
                    "user_id": user_id,
                    "title": None,
                    "created_at": now,
                },
                "$set": {"updated_at": now},
            },
            upsert=True,
        )


async def compress_if_needed(conversation_id: str, model_context_window: int = 128000):
    """Check if compression is needed and compress old messages."""
    # TODO: Phase 4 — Use configurable compression agent from admin settings
    pass
