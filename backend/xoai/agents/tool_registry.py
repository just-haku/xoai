"""Centralized tool registry for agents."""

import inspect
import logging
from typing import Callable, Any, Dict

from xoai.agents.tools import filesystem, shell, web_search, document, voice, zalo

logger = logging.getLogger("xoai.agents.tool_registry")


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.metadata: Dict[str, dict] = {}

    def register(self, name: str, func: Callable, description: str):
        self.tools[name] = func
        
        # Build JSON schema from signature
        sig = inspect.signature(func)
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param in sig.parameters.items():
            if param_name in ["user_id", "bot", "chat_id"]: # Internal context params
                continue
            
            # Basic type mapping
            p_type = "string"
            if param.annotation == int: p_type = "integer"
            elif param.annotation == bool: p_type = "boolean"
            
            parameters["properties"][param_name] = {"type": p_type}
            if param.default is inspect.Parameter.empty:
                parameters["required"].append(param_name)

        self.metadata[name] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }

    def register_mcp_tools(self, server_name: str, tools: list[dict]):
        """Register a list of tool definitions from an MCP server."""
        for t in tools:
            name = t["name"]
            self.metadata[name] = t
            # Mark it so the agent knows to call mcp_manager
            self.metadata[name]["_mcp_server"] = server_name

    def get_definitions(self) -> list[dict]:
        """Return tool definitions in OpenAI/Gemini compatible format."""
        return list(self.metadata.values())

    async def call(self, name: str, args: dict, context: dict) -> Any:
        """Call a tool with provided args and internal context."""
        # Handle MCP calls
        if name in self.metadata and "_mcp_server" in self.metadata[name]:
            from xoai.mcp.client import mcp_manager
            return await mcp_manager.call_tool(
                self.metadata[name]["_mcp_server"], 
                name, 
                args
            )

        if name not in self.tools:
            return f"Error: Tool '{name}' not found."
        
        func = self.tools[name]
        sig = inspect.signature(func)
        
        # Merge provided args with internal context (user_id, etc.)
        call_args = {**args}
        for param_name in sig.parameters:
            if param_name in context:
                call_args[param_name] = context[param_name]
        
        try:
            if inspect.iscoroutinefunction(func):
                return await func(**call_args)
            return func(**call_args)
        except Exception as e:
            return f"Error executing {name}: {e}"


# --- Global Registries ---

async def inject_mcp_tools(reg: ToolRegistry, user_id: str | None = None):
    """Fetch MCP servers from DB and inject their tools into the registry."""
    from xoai.db.mongo import get_db
    db = get_db()
    query = {"user_id": user_id} if user_id else {"user_id": None}
    async for server in db.mcp_servers.find(query):
        reg.register_mcp_tools(server["name"], server.get("tools_cache", []))


def create_admin_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("list_files", filesystem.list_files, "List files in the current workspace.")
    reg.register("read_file", filesystem.read_file, "Read content of a file. (Path jail enforced)")
    reg.register("write_file", filesystem.write_file, "Write content to a file. (Path jail + 15GB quota enforced)")
    reg.register("execute_command", shell.execute_command, "Run a shell command in the user's venv.")
    reg.register("search_web", web_search.search_web, "Search the internet via DuckDuckGo.")
    reg.register("convert_to_docx", document.convert_to_docx, "Convert text content to a .docx file.")
    # Add voice, zalo, etc.
    return reg


def create_user_registry() -> ToolRegistry:
    # Users have same tools but scoped to their personal settings
    return create_admin_registry() 
