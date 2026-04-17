"""Base Agent class — Handles orchestration loop, tool calling, and streaming."""

import asyncio
import json
import logging
from typing import AsyncIterator

from xoai.agents.llm_pool import get_provider
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
        
        # yield self for HITL signal capture back in websocket handler
        yield {"type": "agent_instance", "instance": self}

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
                tool_calls = _normalize_tool_calls(res.get("tool_calls"))
                if not tool_calls:
                    # Final response
                    await save_message(conversation_id, "assistant", res.get("content", ""), user_id=user_id)
                    break

                # 2. Execute tools
                for tc in tool_calls:
                    name, args, tc_id = _parse_tool_call(tc)
                    
                    # Check for HITL
                    tool_meta = self.tools.metadata.get(name, {})
                    if tool_meta.get("requires_approval"):
                        yield {
                            "type": "input_required", 
                            "tool": name, 
                            "args": args,
                            "tc_id": tc_id
                        }
                        # Wait for external signal (via WebSocket handler)
                        self.input_event = asyncio.Event()
                        self.last_input_response = None
                        await self.input_event.wait()
                        
                        if self.last_input_response != "allow":
                            result = "User denied execution."
                            yield {"type": "content", "content": "\n\n*Execution denied by user.*"}
                        else:
                            yield {"type": "tool_start", "tool": name, "args": args}
                            result = await self.tools.call(name, args, context={"user_id": user_id, "conversation_id": conversation_id})
                    else:
                        yield {"type": "tool_start", "tool": name, "args": args}
                        result = await self.tools.call(name, args, context={"user_id": user_id, "conversation_id": conversation_id})
                    
                    yield {"type": "tool_end", "tool": name, "result": result}
                    
                    # Append tool result to history
                    messages.append({
                        "role": "tool", 
                        "tool_call_id": tc_id, 
                        "name": name, 
                        "content": str(result)
                    })

            except Exception as e:
                logger.error(f"Agent {self.name} error: {e}")
                yield {"type": "error", "message": str(e)}
                break


def _normalize_tool_calls(tool_calls):
    if not tool_calls:
        return []
    if isinstance(tool_calls, (list, tuple)):
        return [call for call in tool_calls if call]
    return [tool_calls]


def _parse_tool_call(tool_call) -> tuple[str, dict, str]:
    if isinstance(tool_call, dict):
        function = tool_call.get("function") or {}
        name = function.get("name") or tool_call.get("name")
        raw_args = function.get("arguments", tool_call.get("args", {}))
        tc_id = tool_call.get("id") or name
    elif hasattr(tool_call, "function"):
        name = tool_call.function.name
        raw_args = tool_call.function.arguments
        tc_id = getattr(tool_call, "id", name)
    else:
        name = tool_call.name
        raw_args = getattr(tool_call, "args", {})
        tc_id = name

    if not name:
        raise ValueError("Tool call missing name.")

    if isinstance(raw_args, str):
        args = json.loads(raw_args or "{}")
    else:
        args = raw_args or {}

    if not isinstance(args, dict):
        raise ValueError(f"Tool call '{name}' arguments must be an object.")

    return name, args, tc_id
