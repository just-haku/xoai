"""MCP Client — Orchestrates external tool servers."""

import asyncio
import logging
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("xoai.mcp.client")


class McpManager:
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}

    async def connect_stdio(self, name: str, command: str, args: List[str]):
        """Connect to an MCP server via stdio and discover tools."""
        server_params = StdioServerParameters(command=command, args=args)
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

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        """Call a tool on a connected MCP server."""
        # TODO: Implement persistent session management or on-demand connection
        return f"MCP tool call {tool_name} on {server_name} not yet fully persistent."


mcp_manager = McpManager()
