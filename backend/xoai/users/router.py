"""User management routes (admin-only)."""

from fastapi import APIRouter, HTTPException, Depends

from xoai.auth.dependencies import require_admin
from xoai.users import service

router = APIRouter()


@router.get("/")
async def list_users(skip: int = 0, limit: int = 50, _=Depends(require_admin)):
    return await service.list_users(skip, limit)


@router.post("/{user_id}/approve")
async def approve_user(user_id: str, _=Depends(require_admin)):
    ok = await service.approve_user(user_id)
    if not ok:
        raise HTTPException(404, "User not found or not pending")
    return {"message": f"User {user_id} approved"}


@router.post("/{user_id}/disable")
async def disable_user(user_id: str, _=Depends(require_admin)):
    ok = await service.disable_user(user_id)
    if not ok:
        raise HTTPException(404, "User not found")
    return {"message": f"User {user_id} disabled"}
