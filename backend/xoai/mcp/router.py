"""MCP Server CRUD router."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from xoai.auth.dependencies import require_admin
from xoai.db.mongo import get_db
from xoai.mcp.client import mcp_manager

router = APIRouter()


@router.get("/")
async def list_mcp_servers(admin: dict = Depends(require_admin)):
    """List all configured MCP servers."""
    db = get_db()
    cursor = db.mcp_servers.find()
    servers = await cursor.to_list(100)
    for s in servers:
        s["id"] = str(s.pop("_id"))
    return servers


@router.post("/")
async def add_mcp_server(config: dict, admin: dict = Depends(require_admin)):
    """Add a new MCP server and discover its tools."""
    db = get_db()
    
    # Validate connection and discover tools
    tools = await mcp_manager.connect_stdio(
        config["name"], 
        config["command"], 
        config.get("args", [])
    )
    
    if not tools:
        logger.warning(f"No tools discovered for {config['name']}")

    doc = {
        "name": config["name"],
        "command": config["command"],
        "args": config.get("args", []),
        "tools_cache": tools,
    }
    result = await db.mcp_servers.insert_one(doc)
    return {"id": str(result.inserted_id), "tools": tools}
