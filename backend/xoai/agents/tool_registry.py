"""Centralized tool registry for agents."""

import inspect
import logging
import re
from typing import Callable, Any, Dict

from xoai.agents.tools import filesystem, python_exec, shell, web_search, document, voice, zalo, experience

logger = logging.getLogger("xoai.agents.tool_registry")


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.metadata: Dict[str, dict] = {}

    def register(
        self,
        name: str,
        func: Callable,
        description: str,
        requires_approval: bool = False,
        *,
        risk_class: str = "read_only",
        network_policy: str = "network_disabled",
    ):
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
            "parameters": parameters,
            "requires_approval": requires_approval,
            "risk_class": risk_class,
            "network_policy": network_policy,
        }

    def register_mcp_tools(self, server_name: str, tools: list[dict], user_id: str | None = None, allowed_roles: list[str] | None = None):
        """Register a list of tool definitions from an MCP server."""
        for t in tools:
            source_name = t["name"]
            safe_server = re.sub(r"[^a-zA-Z0-9_]+", "_", server_name)
            safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", source_name)
            name = f"mcp__{safe_server}__{safe_name}"

            self.metadata[name] = {
                "name": name,
                "description": f"[MCP:{server_name}] {t.get('description', source_name)}",
                "parameters": t.get("inputSchema") or t.get("parameters") or {
                    "type": "object",
                    "properties": {},
                },
                "requires_approval": False,
                "_mcp_server": server_name,
                "_mcp_tool_name": source_name,
                "_mcp_user_id": user_id,
                "allowed_roles": allowed_roles or ["admin", "user"],
            }

    def get_definitions(self) -> list[dict]:
        """Return tool definitions in OpenAI/Gemini compatible format."""
        defs = []
        for meta in self.metadata.values():
            defs.append({
                "name": meta["name"],
                "description": meta["description"],
                "parameters": meta.get("parameters", {"type": "object", "properties": {}}),
                "requires_approval": meta.get("requires_approval", False),
                "risk_class": meta.get("risk_class", "read_only"),
                "network_policy": meta.get("network_policy", "network_disabled"),
            })
        return defs

    async def call(self, name: str, args: dict, context: dict) -> Any:
        """Call a tool with provided args and internal context."""
        # Handle MCP calls
        if name in self.metadata and "_mcp_server" in self.metadata[name]:
            from xoai.mcp.client import mcp_manager
            return await mcp_manager.call_tool(
                self.metadata[name]["_mcp_server"], 
                self.metadata[name]["_mcp_tool_name"], 
                args,
                user_id=self.metadata[name].get("_mcp_user_id") or context.get("user_id"),
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

async def inject_mcp_tools(reg: ToolRegistry, user_id: str | None = None, role: str = "user"):
    """Fetch MCP servers from DB and inject their tools into the registry."""
    from xoai.db.mongo import get_db
    db = get_db()
    query = {"enabled": {"$ne": False}}
    if user_id:
        query["$or"] = [{"user_id": None}, {"user_id": user_id}]
    else:
        query["user_id"] = None
    async for server in db.mcp_servers.find(query):
        allowed_roles = server.get("allowed_roles") or (["admin", "user"] if not server.get("user_id") else ["user"])
        if role not in allowed_roles:
            continue
        reg.register_mcp_tools(
            server["name"],
            server.get("tools_cache", []),
            user_id=server.get("user_id"),
            allowed_roles=allowed_roles,
        )


def create_admin_registry(read_only: bool = False) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("list_files", filesystem.list_files, "List files in the current workspace.", risk_class="read_only")
    reg.register("read_file", filesystem.read_file, "Read content of a file. (Path jail enforced)", risk_class="read_only")
    reg.register("lookup_experience", experience.lookup_experience_tool, "Retrieve prior lessons and experience insights for a profile.", risk_class="read_only")
    if not read_only:
        reg.register("write_file", filesystem.write_file, "Write content to a file. (Path jail + 15GB quota enforced)", risk_class="mutating_high")
        reg.register("execute_command", shell.execute_command, "Run a shell command in the user's venv.", requires_approval=True, risk_class="operator_sensitive", network_policy="network_allowlisted")
        reg.register("execute_python_code", python_exec.execute_python_code, "Execute Python code in an isolated sandbox container with zero-trust network isolation.", risk_class="operator_sensitive", network_policy="network_disabled")
    reg.register("search_web", web_search.search_web, "Search the internet via DuckDuckGo.", risk_class="external_side_effect", network_policy="network_full_user_scoped")
    reg.register("convert_to_docx", document.convert_to_docx, "Convert text content to a .docx file.", risk_class="mutating_low")
    # Add voice, zalo, etc.
    return reg


def create_user_registry() -> ToolRegistry:
    # Users have same tools but scoped to their personal settings
    return create_admin_registry() 
