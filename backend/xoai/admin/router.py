"""Admin dashboard routes: settings CRUD, stats."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from xoai.auth.dependencies import require_admin
from xoai.admin import service
from xoai.db.mongo import get_db

router = APIRouter()


class SettingUpdate(BaseModel):
    key: str
    value: dict


@router.get("/settings")
async def list_settings(_=Depends(require_admin)):
    """List all setting keys (values are encrypted, returned on individual get)."""
    return await service.list_setting_keys()


@router.get("/settings/{key}")
async def get_setting(key: str, _=Depends(require_admin)):
    val = await service.get_setting(key)
    if val is None:
        raise HTTPException(404, f"Setting '{key}' not found")
    return {"key": key, "value": val}


@router.put("/settings")
async def set_setting(req: SettingUpdate, _=Depends(require_admin)):
    await service.set_setting(req.key, req.value)
    return {"message": f"Setting '{req.key}' saved"}


@router.delete("/settings/{key}")
async def delete_setting(key: str, _=Depends(require_admin)):
    ok = await service.delete_setting(key)
    if not ok:
        raise HTTPException(404, f"Setting '{key}' not found")
    return {"message": f"Setting '{key}' deleted"}


@router.get("/stats")
async def dashboard_stats(_=Depends(require_admin)):
    db = get_db()
    total_users = await db.users.count_documents({})
    pending_users = await db.users.count_documents({"status": "pending"})
    total_conversations = await db.conversations.count_documents({})
    open_tickets = await db.tickets.count_documents({"status": "open"})

    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "total_conversations": total_conversations,
        "open_tickets": open_tickets,
    }
