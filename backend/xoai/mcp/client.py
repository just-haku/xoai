"""MCP Client — Orchestrates external tool servers."""

import asyncio
import logging
from contextlib import AsyncExitStack
from datetime import datetime, timezone
from typing import List, Dict, Any

from bson import ObjectId
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("xoai.mcp.client")


class ManagedMcpSession:
    def __init__(self, name: str, scope_key: str, stack: AsyncExitStack, session: ClientSession):
        self.name = name
        self.scope_key = scope_key
        self.stack = stack
        self.session = session


class McpManager:
    def __init__(self):
        self.sessions: Dict[str, ManagedMcpSession] = {}
        self.max_reconnect_attempts = 2

    async def connect_stdio(self, name: str, command: str, args: List[str], env: dict | None = None):
        """Connect to an MCP server via stdio and discover tools."""
        server_params = StdioServerParameters(command=command, args=args, env=env)
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    logger.info(f"Connected to MCP server '{name}'. Discovered {len(tools_result.tools)} tools.")
                    return [t.model_dump() for t in tools_result.tools]
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{name}': {e}")
            return []

    async def ensure_connected(self, server_name: str, user_id: str | None = None) -> ManagedMcpSession:
        key = self._session_key(server_name, user_id)
        managed = self.sessions.get(key)
        if managed and await self.ping_server(server_name, user_id=user_id):
            return managed
        if managed:
            await self.disconnect_server(server_name, user_id=user_id)

        server = await self._load_server_config(server_name, user_id=user_id)
        if not server:
            raise ValueError(f"MCP server '{server_name}' is not configured.")
        if server.get("transport", "stdio") != "stdio":
            raise ValueError(f"Unsupported MCP transport: {server.get('transport')}")

        stack = AsyncExitStack()
        server_params = StdioServerParameters(
            command=server["command"],
            args=server.get("args", []),
            env=server.get("env"),
        )
        read, write = await stack.enter_async_context(stdio_client(server_params))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        managed = ManagedMcpSession(server_name, key, stack, session)
        self.sessions[key] = managed
        await self._mark_server_status(server_name, user_id, status="ready", error=None, touched_heartbeat=True)
        return managed

    async def refresh_server(self, server_name: str, user_id: str | None = None) -> list[dict]:
        managed = self.sessions.pop(self._session_key(server_name, user_id), None)
        if managed:
            await managed.stack.aclose()

        server = await self._load_server_config(server_name, user_id=user_id)
        if not server:
            raise ValueError(f"MCP server '{server_name}' is not configured.")

        tools = await self.connect_stdio(
            server_name,
            server["command"],
            server.get("args", []),
            env=server.get("env"),
        )

        from xoai.db.mongo import get_db

        db = get_db()
        await db.mcp_servers.update_one(
            {"name": server_name, "user_id": server.get("user_id")},
            {
                "$set": {
                    "tools_cache": tools,
                    "status": "ready" if tools else "error",
                    "last_connected_at": datetime.now(timezone.utc),
                    "last_heartbeat_at": datetime.now(timezone.utc) if tools else server.get("last_heartbeat_at"),
                    "last_error": None if tools else "No tools discovered",
                }
            },
        )
        return tools

    async def refresh_server_by_id(self, server_id: str) -> list[dict]:
        server = await self._load_server_by_id(server_id)
        if not server:
            raise ValueError("MCP server not found.")
        return await self.refresh_server(server["name"], user_id=server.get("user_id"))

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict, user_id: str | None = None) -> Any:
        """Call a tool on a connected MCP server."""
        attempt = 0
        while True:
            try:
                managed = await self.ensure_connected(server_name, user_id=user_id)
                result = await managed.session.call_tool(tool_name, arguments or {})
                await self._mark_server_status(server_name, user_id, status="ready", error=None, touched_heartbeat=True)
                return self._serialize_result(result)
            except Exception as exc:
                attempt += 1
                await self._mark_server_status(
                    server_name,
                    user_id,
                    status="error",
                    error=str(exc),
                    increment_reconnect=attempt <= self.max_reconnect_attempts,
                )
                await self.disconnect_server(server_name, user_id=user_id)
                if attempt > self.max_reconnect_attempts:
                    raise

    async def disconnect_all(self) -> None:
        for key, managed in list(self.sessions.items()):
            await managed.stack.aclose()
            self.sessions.pop(key, None)

    async def disconnect_server(self, server_name: str, user_id: str | None = None) -> None:
        key = self._session_key(server_name, user_id)
        managed = self.sessions.pop(key, None)
        if managed:
            await managed.stack.aclose()

    async def _load_server_config(self, server_name: str, user_id: str | None = None) -> dict | None:
        from xoai.db.mongo import get_db

        db = get_db()
        query = {"name": server_name, "enabled": {"$ne": False}}
        if user_id:
            query["$or"] = [{"user_id": user_id}, {"user_id": None}]
        else:
            query["user_id"] = None

        return await db.mcp_servers.find_one(query, sort=[("user_id", -1)])

    async def _load_server_by_id(self, server_id: str) -> dict | None:
        from xoai.db.mongo import get_db

        db = get_db()
        return await db.mcp_servers.find_one({"_id": ObjectId(server_id)})

    async def ping_server(self, server_name: str, user_id: str | None = None) -> bool:
        key = self._session_key(server_name, user_id)
        managed = self.sessions.get(key)
        if not managed:
            return False
        try:
            await managed.session.list_tools()
            await self._mark_server_status(server_name, user_id, status="ready", error=None, touched_heartbeat=True)
            return True
        except Exception as exc:
            logger.warning("MCP ping failed for %s: %s", key, exc)
            await self._mark_server_status(server_name, user_id, status="error", error=str(exc))
            return False

    def _serialize_result(self, result: Any) -> Any:
        if hasattr(result, "content"):
            parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                elif hasattr(item, "model_dump"):
                    parts.append(str(item.model_dump()))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return str(result)

    def _session_key(self, server_name: str, user_id: str | None = None) -> str:
        return f"{user_id or 'global'}::{server_name}"

    async def _mark_server_status(
        self,
        server_name: str,
        user_id: str | None,
        *,
        status: str,
        error: str | None,
        touched_heartbeat: bool = False,
        increment_reconnect: bool = False,
    ) -> None:
        from xoai.db.mongo import get_db

        db = get_db()
        update = {
            "$set": {
                "status": status,
                "last_error": error,
            }
        }
        if touched_heartbeat:
            update["$set"]["last_heartbeat_at"] = datetime.now(timezone.utc)
        if increment_reconnect:
            update["$inc"] = {"reconnect_count": 1}
        await db.mcp_servers.update_one({"name": server_name, "user_id": user_id}, update)


mcp_manager = McpManager()
