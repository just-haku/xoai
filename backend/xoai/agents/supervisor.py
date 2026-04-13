"""Agent 0 — The Supervisor / Bridge.

For Admin: Classifies intent → routes to Agent 1, Agent 2, or both.
For Users: Lightweight bridge — sanitizes input, routes to user's personal agent.
No tool access — pure routing intelligence.
"""

import logging
import asyncio
from datetime import datetime, timezone

from xoai.agents.base import BaseAgent
from xoai.agents.llm_pool import get_agent_config, llm_pool
from xoai.db.mongo import db

logger = logging.getLogger("xoai.agents.supervisor")

SUPERVISOR_PROMPT = """
You are XOAI SUPERVISOR (Agent 0). Your job is to route admin requests.
ADMIN is a high-level user with two powerful sub-agents:
1. Agent 1 (Architect): For research, planning, and task breakdown. (Safe, read-only)
2. Agent 2 (Executor): For file synthesis, coding, and shell execution. (Powerful, tool-rich)

CLASSIFY the user's intent:
- If they ask for a PLAN, RESEARCH, or ANALYSIS -> Route to ARCHITECT.
- If they ask to DO something, BUILD, FIX, or RUN code -> Route to EXECUTOR.
- If it's a casual chat or question you can answer yourself -> REPLY directly.

Response format for routing:
ROUTE: [ARCHITECT|EXECUTOR|DIRECT]
REASON: [Brief reason]
"""

async def process_message(user: dict, message: str, conversation_id: str, channel: str = "web"):
    """Entry point for all user messages. Routes based on user role."""
    user_role = user.get("role", "user")

    # Check if first message to trigger auto-titling
    chat = await db.conversations.find_one({"chat_id": conversation_id})
    if chat and not chat.get("title"):
        asyncio.create_task(_handle_new_conversation(conversation_id, message))

    if user_role == "admin":
        return await _route_admin(user, message, conversation_id, channel)
    else:
        return await _route_user(user, message, conversation_id, channel)


async def _route_admin(user: dict, message: str, conversation_id: str, channel: str):
    """Admin intent classification via Agent 0."""
    config = await get_agent_config("agent_0")
    if not config:
        return {"error": "Agent 0 not configured."}

    agent = BaseAgent("Agent 0", config, SUPERVISOR_PROMPT)
    
    classification_text = ""
    async for chunk in agent.chat(user["id"], conversation_id, message, []):
        if chunk["type"] == "content":
            classification_text += chunk["content"]
    
    route = "DIRECT"
    if "ROUTE: ARCHITECT" in classification_text: route = "ARCHITECT"
    elif "ROUTE: EXECUTOR" in classification_text: route = "EXECUTOR"
    
    logger.info(f"[Agent 0] Admin routing: {route}. channel={channel}")
    
    if route == "EXECUTOR":
        from xoai.agents.executor import execute
        return await execute(message, conversation_id, user["id"])
    elif route == "ARCHITECT":
        from xoai.agents.architect import plan
        return await plan(message, conversation_id, user["id"])
    
    return {"type": "content", "content": classification_text}


async def _route_user(user: dict, message: str, conversation_id: str, channel: str):
    """User bridge: route to personal agent with ticket interception."""
    support_keywords = ["help", "support", "ticket", "issue", "problem", "không", "hỗ trợ"]
    if any(kw in message.lower() for kw in support_keywords):
        await db.tickets.insert_one({
            "user_id": user["id"],
            "status": "pending",
            "message": message,
            "created_at": datetime.now(timezone.utc)
        })
        async def intercepted_stream():
            yield {"type": "content", "content": "I've detected you need help. I've created a support ticket."}
        return intercepted_stream()

    from xoai.agents.user_agent import process
    return await process(user["id"], message, conversation_id, channel)


async def _handle_new_conversation(chat_id: str, first_msg: str):
    """Generates a title for new conversations using Agent 0's intent model."""
    prompt = f"Analyze message and provide 3-5 word title for chat session. Message: {first_msg}"
    try:
        response = await llm_pool.generate(prompt, model="gemini-1.5-flash")
        title = response.strip().strip('"')
        await db.conversations.update_one(
            {"chat_id": chat_id},
            {"$set": {"title": title, "updated_at": datetime.now(timezone.utc)}}
        )
    except Exception as e:
        logger.error(f"Failed to auto-title chat {chat_id}: {e}")
