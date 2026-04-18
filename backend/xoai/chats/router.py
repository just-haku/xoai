from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from xoai.auth.dependencies import get_current_user
from xoai.db.mongo import db
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel

router = APIRouter()


def _ensure_chat_write_allowed(user: dict) -> None:
    if user.get("proxy_by"):
        raise HTTPException(status_code=403, detail="Chat is read-only in God Mode")


class ForkChatRequest(BaseModel):
    index: int | None = None
    content: str | None = None


class RenameChatRequest(BaseModel):
    title: str


def _serialize(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {"id" if key == "_id" else key: _serialize(item) for key, item in value.items()}
    return value


@router.get("/")
async def get_chats(user: dict = Depends(get_current_user)):
    chats = await db.conversations.find({"user_id": user["id"]}).sort("updated_at", -1).to_list(100)
    return {"status": "success", "chats": _serialize(chats)}

@router.get("/{chat_id}/messages")
async def get_chat_messages(chat_id: str, user: dict = Depends(get_current_user)):
    chat = await db.conversations.find_one({"chat_id": chat_id, "user_id": user["id"]})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    messages = await db.messages.find({"conversation_id": chat_id}).sort("created_at", 1).to_list(1000)
    return {"status": "success", "messages": _serialize(messages)}

@router.post("/{chat_id}/fork")
async def fork_chat(chat_id: str, data: ForkChatRequest | None = None, user: dict = Depends(get_current_user)):
    _ensure_chat_write_allowed(user)
    # Legacy fork (copy all) or Fork-at (copy up to index)
    index = data.index if data else None
    new_content = data.content if data else None
    
    original = await db.conversations.find_one({"chat_id": chat_id, "user_id": user["id"]})
    if not original:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    messages = await db.messages.find({"conversation_id": chat_id}).sort("created_at", 1).to_list(500)
    if index is not None:
        messages = messages[:index]
        if new_content:
            messages.append({"role": "user", "content": new_content, "created_at": datetime.now(timezone.utc)})
            
    new_chat_id = str(uuid.uuid4())
    new_chat = {
        "chat_id": new_chat_id,
        "user_id": user["id"],
        "title": f"Branch of {original.get('title', 'Untitled')}",
        "summary_compressed": None,
        "message_count": len(messages),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    await db.conversations.insert_one(new_chat)
    if messages:
        copied_messages = []
        now = datetime.now(timezone.utc)
        for message in messages:
            copied = {
                key: value
                for key, value in message.items()
                if key not in {"_id", "conversation_id"}
            }
            copied["conversation_id"] = new_chat_id
            copied.setdefault("created_at", now)
            copied_messages.append(copied)
        await db.messages.insert_many(copied_messages)
    return {"status": "success", "chat_id": new_chat_id}

@router.patch("/{chat_id}")
async def rename_chat(chat_id: str, data: RenameChatRequest, user: dict = Depends(get_current_user)):
    _ensure_chat_write_allowed(user)
    title = data.title
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
    _ensure_chat_write_allowed(user)
    result = await db.conversations.delete_one({"chat_id": chat_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")
    await db.messages.delete_many({"conversation_id": chat_id})
    return {"status": "success"}
