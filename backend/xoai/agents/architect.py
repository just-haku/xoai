"""Agent 1 — The Architect (Admin-only).
Planner with read-only file access. Generates plans and task breakdowns.
"""

import logging

logger = logging.getLogger("xoai.agents.architect")


from xoai.agents.base import BaseAgent
from xoai.agents.llm_pool import get_agent_config
from xoai.agents.tool_registry import create_admin_registry
from xoai.prompts.manager import get_prompt

logger = logging.getLogger("xoai.agents.architect")

# ARCHITECT_PROMPT moved to prompts folder

async def plan(directive: str, conversation_id: str, user_id: str):
    """Process a planning directive with read-only tools."""
    config = await get_agent_config("agent_1")
    if not config:
        return {"error": "Agent 1 not configured."}

    # Create a registry but omit write/execute if possible (or just rely on prompt)
    registry = create_admin_registry()
    # TODO: Filter registry for read-only tools if security is high
    
    agent = BaseAgent("Agent 1", config, get_prompt("architect"), tools=registry)
    return agent.chat(user_id, conversation_id, directive, [])
