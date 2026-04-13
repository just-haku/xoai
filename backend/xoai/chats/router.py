from fastapi import APIRouter, Depends, HTTPException
from typing import List
from xoai.auth.router import get_current_user
from xoai.db.mongo import db
import uuid
from datetime import datetime, timezone

router = APIRouter()

@router.get("/")
async def get_chats(user: dict = Depends(get_current_user)):
    chats = await db.conversations.find({"user_id": user["id"]}).to_list(100)
    return {"status": "success", "chats": chats}

@router.post("/{chat_id}/fork")
async def fork_chat(chat_id: str, user: dict = Depends(get_current_user)):
    original = await db.conversations.find_one({"chat_id": chat_id, "user_id": user["id"]})
    if not original:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    new_chat_id = str(uuid.uuid4())
    new_chat = {
        "chat_id": new_chat_id,
        "user_id": user["id"],
        "title": f"Fork of {original.get('title', 'Untitled')}",
        "messages": original.get("messages", []),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await db.conversations.insert_one(new_chat)
    return {"status": "success", "chat_id": new_chat_id}

@router.patch("/{chat_id}")
async def rename_chat(chat_id: str, data: dict, user: dict = Depends(get_current_user)):
    title = data.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Title required")
    
    result = await db.conversations.update_one(
        {"chat_id": chat_id, "user_id": user["id"]},
        {"$set": {"title": title, "updated_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success"}

@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, user: dict = Depends(get_current_user)):
    result = await db.conversations.delete_one({"chat_id": chat_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success"}
