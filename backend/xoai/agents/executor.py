"""Agent 2 — The Executor (Admin-only).
Full tool access + sub-agent spawning.
"""

import logging

logger = logging.getLogger("xoai.agents.executor")


from xoai.agents.base import BaseAgent
from xoai.agents.llm_pool import get_agent_config
from xoai.agents.tool_registry import create_admin_registry
from xoai.prompts.manager import get_prompt

logger = logging.getLogger("xoai.agents.executor")

# EXECUTOR_PROMPT moved to prompts folder

async def execute(directive: str, conversation_id: str, user_id: str):
    """Execute a task with full tools."""
    config = await get_agent_config("agent_2")
    if not config:
        return {"error": "Agent 2 not configured."}

    registry = create_admin_registry()
    agent = BaseAgent("Agent 2", config, get_prompt("executor"), tools=registry)
    
    # For sync-style call from supervisor, we'll return the final result or stream
    # Phase 3 simplification: just return the stream generator
    return agent.chat(user_id, conversation_id, directive, [])
