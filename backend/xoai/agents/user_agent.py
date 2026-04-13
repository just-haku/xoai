"""User's personal agent — activated with user's own API key."""

import logging

logger = logging.getLogger("xoai.agents.user_agent")


from xoai.agents.base import BaseAgent
from xoai.agents.llm_pool import get_user_agent_key
from xoai.agents.tool_registry import create_user_registry

logger = logging.getLogger("xoai.agents.user_agent")

USER_AGENT_PROMPT = """
You are XOAI, a personal AI assistant. Your goal is to help the user with their tasks.
You have access to their private workspace and various technical tools.
Always be professional, concise, and helpful.
"""

async def process(user_id: str, message: str, conversation_id: str, channel: str = "web"):
    """Process a message for a regular user via their personal agent."""
    config = await get_user_agent_key(user_id)
    if not config:
        return {"type": "error", "message": "Personal API key not configured. Please go to Settings."}

    registry = create_user_registry()
    agent = BaseAgent("UserAgent", config, USER_AGENT_PROMPT, tools=registry)
    
    # In Phase 3, we'll return the stream
    return agent.chat(user_id, conversation_id, message, [])
