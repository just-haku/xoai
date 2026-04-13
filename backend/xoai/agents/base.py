"""Base Agent class — Handles orchestration loop, tool calling, and streaming."""

import json
import logging
from typing import AsyncIterator

from xoai.agents.llm_pool import get_provider, get_fallback_key
from xoai.agents.tool_registry import ToolRegistry
from xoai.agents.memory import save_message

logger = logging.getLogger("xoai.agents.base")


class BaseAgent:
    def __init__(
        self,
        name: str,
        config: dict,
        system_prompt: str,
        tools: ToolRegistry | None = None,
    ):
        self.name = name
        self.config = config
        self.system_prompt = system_prompt
        self.tools = tools
        self.provider = None

    async def _ensure_provider(self):
        if not self.provider:
            self.provider = await get_provider(self.config)

    async def chat(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        history: list[dict],
    ) -> AsyncIterator[dict]:
        """Process a message and yield response chunks + tool status."""
        await self._ensure_provider()
        
        # Prepare context
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        # Tool definitions
        tool_defs = self.tools.get_definitions() if self.tools else []
        
        # For simplicity in Phase 3, we'll do the orchestration loop here
        # Note: Streaming with tool calls is complex; we'll handle tool calls non-streaming
        # and text streaming separately.

        for step in range(10):  # Max 10 tool steps to prevent infinite loops
            try:
                # 1. Get completion
                res = await self.provider.chat(
                    model=self.config["model"],
                    messages=messages,
                    tools=tool_defs,
                )
                
                # yield text if any
                if res.get("content"):
                    yield {"type": "content", "content": res["content"]}
                    messages.append({"role": "assistant", "content": res["content"]})
                
                # check for tool calls
                tool_calls = res.get("tool_calls")
                if not tool_calls:
                    # Final response
                    await save_message(conversation_id, "assistant", res.get("content", ""))
                    break

                # 2. Execute tools
                for tc in tool_calls:
                    # Generic handling for both OpenAI/Gemini SDK structures
                    if hasattr(tc, "function"): # OpenAI style
                        name = tc.function.name
                        args = json.loads(tc.function.arguments)
                    else: # Gemini style (assumed)
                        name = tc.name
                        args = tc.args
                    
                    yield {"type": "tool_start", "tool": name, "args": args}
                    
                    result = await self.tools.call(
                        name, 
                        args, 
                        context={"user_id": user_id, "conversation_id": conversation_id}
                    )
                    
                    yield {"type": "tool_end", "tool": name, "result": result}
                    
                    # Append tool result to history
                    messages.append({
                        "role": "tool", 
                        "tool_call_id": getattr(tc, "id", name), 
                        "name": name, 
                        "content": str(result)
                    })

            except Exception as e:
                logger.error(f"Agent {self.name} error: {e}")
                yield {"type": "error", "message": str(e)}
                break
