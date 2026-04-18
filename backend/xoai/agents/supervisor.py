"""Agent 0 — The Supervisor / Bridge.

For Admin: Classifies intent → routes to Agent 1, Agent 2, or both.
For Users: Lightweight bridge — sanitizes input, routes to user's personal agent.
No tool access — pure routing intelligence.
"""

import logging
from datetime import datetime, timezone

from xoai.agents.llm_pool import llm_pool
from xoai.agents.runtime import run_query
from xoai.db.mongo import db
from xoai.jobs import job_manager
from xoai.prompts.manager import get_prompt

logger = logging.getLogger("xoai.agents.supervisor")

async def process_message(user: dict, message: str, conversation_id: str, channel: str = "web"):
    # Check if first message to trigger auto-titling
    chat = await db.conversations.find_one({"chat_id": conversation_id})
    if chat and not chat.get("title"):
        await job_manager.enqueue("auto_title", {"chat_id": conversation_id, "first_msg": message})

    return run_query(user, message, conversation_id, channel)


async def generate_auto_title(chat_id: str, first_msg: str):
    """Generates a title for new conversations using Agent 0's intent model."""
    prompt = get_prompt("auto_title", first_msg=first_msg)
    try:
        response = await llm_pool.generate(prompt, model="gemini-1.5-flash")
        title = response.strip().strip('"')
        await db.conversations.update_one(
            {"chat_id": chat_id},
            {"$set": {"title": title, "updated_at": datetime.now(timezone.utc)}}
        )
    except Exception as e:
        logger.error(f"Failed to auto-title chat {chat_id}: {e}")
