"""Agent 2 — The Executor (Admin-only).
Full tool access + sub-agent spawning.
"""

import logging

logger = logging.getLogger("xoai.agents.executor")


from xoai.agents.base import BaseAgent
from xoai.agents.llm_pool import get_agent_config
from xoai.agents.tool_registry import create_admin_registry

logger = logging.getLogger("xoai.agents.executor")

EXECUTOR_PROMPT = """
You are XOAI EXECUTOR (Agent 2). You are a master software engineer and sysadmin.
You have FULL access to the user's workspace, shell, and internet.
Your goal is to fulfill the directive with absolute precision.

Rules:
1. THINK before you act. 
2. Use tools to verify your assumptions (e.g., list_files before read_file).
3. Always check for errors in tool outputs.
4. Speak only when necessary or to report progress.
5. If you are stuck, explain why.
"""

async def execute(directive: str, conversation_id: str, user_id: str):
    """Execute a task with full tools."""
    config = await get_agent_config("agent_2")
    if not config:
        return {"error": "Agent 2 not configured."}

    registry = create_admin_registry()
    agent = BaseAgent("Agent 2", config, EXECUTOR_PROMPT, tools=registry)
    
    # For sync-style call from supervisor, we'll return the final result or stream
    # Phase 3 simplification: just return the stream generator
    return agent.chat(user_id, conversation_id, directive, [])
