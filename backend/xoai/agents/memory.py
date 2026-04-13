"""Conversation memory + compression."""

import logging

logger = logging.getLogger("xoai.agents.memory")


async def get_conversation_messages(conversation_id: str, limit: int = 50) -> list:
    """Fetch recent messages for a conversation."""
    from xoai.db.mongo import get_db
    db = get_db()
    cursor = db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", -1).limit(limit)
    messages = await cursor.to_list(limit)
    messages.reverse()
    return messages


async def save_message(conversation_id: str, role: str, content: str, **kwargs):
    """Save a message to the conversation."""
    from xoai.db.mongo import get_db
    from datetime import datetime, timezone
    db = get_db()
    doc = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "tool_calls": kwargs.get("tool_calls", []),
        "channel_metadata": kwargs.get("channel_metadata", {}),
        "created_at": datetime.now(timezone.utc),
    }
    await db.messages.insert_one(doc)


async def compress_if_needed(conversation_id: str, model_context_window: int = 128000):
    """Check if compression is needed and compress old messages."""
    # TODO: Phase 4 — Use configurable compression agent from admin settings
    pass
