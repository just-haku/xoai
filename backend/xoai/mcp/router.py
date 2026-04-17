"""MCP Server CRUD router."""

import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from xoai.auth.dependencies import require_admin
from xoai.db.mongo import get_db
from xoai.mcp.client import mcp_manager

router = APIRouter()
logger = logging.getLogger("xoai.mcp.router")


class McpServerConfig(BaseModel):
    name: str
    transport: str = "stdio"
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict | None = None
    user_id: str | None = None
    enabled: bool = True
    allowed_roles: list[str] | None = None


@router.get("/")
async def list_mcp_servers(admin: dict = Depends(require_admin)):
    """List all configured MCP servers."""
    db = get_db()
    cursor = db.mcp_servers.find()
    servers = await cursor.to_list(100)
    for s in servers:
        s["id"] = str(s.pop("_id"))
        s["scope"] = "user" if s.get("user_id") else "global"
    return servers


@router.post("/")
async def add_mcp_server(config: McpServerConfig, admin: dict = Depends(require_admin)):
    """Add a new MCP server and discover its tools."""
    db = get_db()
    payload = config.model_dump()
    
    # Validate connection and discover tools
    tools = await mcp_manager.connect_stdio(
        payload["name"], 
        payload["command"], 
        payload.get("args", []),
        env=payload.get("env"),
    )
    
    if not tools:
        logger.warning(f"No tools discovered for {payload['name']}")

    doc = {
        "name": payload["name"],
        "transport": payload.get("transport", "stdio"),
        "command": payload["command"],
        "args": payload.get("args", []),
        "env": payload.get("env"),
        "user_id": payload.get("user_id"),
        "enabled": payload.get("enabled", True),
        "allowed_roles": payload.get("allowed_roles") or (["admin", "user"] if not payload.get("user_id") else ["user"]),
        "status": "ready" if tools else "error",
        "tools_cache": tools,
        "last_heartbeat_at": datetime.now(timezone.utc) if tools else None,
        "last_error": None if tools else "No tools discovered",
        "reconnect_count": 0,
    }
    result = await db.mcp_servers.insert_one(doc)
    return {"id": str(result.inserted_id), "tools": tools}


@router.put("/{server_id}")
async def update_mcp_server(server_id: str, config: McpServerConfig, admin: dict = Depends(require_admin)):
    db = get_db()
    existing = await db.mcp_servers.find_one({"_id": ObjectId(server_id)})
    if not existing:
        raise HTTPException(404, "MCP server not found")

    payload = config.model_dump()
    tools = await mcp_manager.connect_stdio(
        payload["name"],
        payload["command"],
        payload.get("args", []),
        env=payload.get("env"),
    )

    await mcp_manager.disconnect_server(existing["name"], user_id=existing.get("user_id"))

    await db.mcp_servers.update_one(
        {"_id": ObjectId(server_id)},
        {
            "$set": {
                "name": payload["name"],
                "transport": payload.get("transport", "stdio"),
                "command": payload["command"],
                "args": payload.get("args", []),
                "env": payload.get("env"),
                "user_id": payload.get("user_id"),
                "enabled": payload.get("enabled", True),
                "allowed_roles": payload.get("allowed_roles") or (["admin", "user"] if not payload.get("user_id") else ["user"]),
                "tools_cache": tools,
                "status": "ready" if tools else "error",
                "last_heartbeat_at": datetime.now(timezone.utc) if tools else None,
                "last_error": None if tools else "No tools discovered",
            }
        },
    )
    return {"status": "ok", "tools": tools}


@router.delete("/{server_id}")
async def delete_mcp_server(server_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    existing = await db.mcp_servers.find_one({"_id": ObjectId(server_id)})
    if not existing:
        raise HTTPException(404, "MCP server not found")

    await mcp_manager.disconnect_server(existing["name"], user_id=existing.get("user_id"))
    await db.mcp_servers.delete_one({"_id": ObjectId(server_id)})
    return {"status": "ok"}


@router.post("/{server_id}/refresh")
async def refresh_mcp_server(server_id: str, admin: dict = Depends(require_admin)):
    try:
        tools = await mcp_manager.refresh_server_by_id(server_id)
        return {"status": "ok", "tools": tools}
    except Exception as e:
        raise HTTPException(400, str(e))
