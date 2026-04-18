import pytest
from fastapi import HTTPException
from datetime import datetime, timezone

from bson import ObjectId

from xoai.chats.router import _ensure_chat_write_allowed, _serialize


def test_serialize_converts_mongo_types_for_chat_payloads():
    now = datetime.now(timezone.utc)
    payload = {
        "_id": ObjectId("64f000000000000000000001"),
        "chat_id": "chat-1",
        "updated_at": now,
        "messages": [{"_id": ObjectId("64f000000000000000000002"), "created_at": now}],
    }

    serialized = _serialize(payload)

    assert serialized["id"] == "64f000000000000000000001"
    assert serialized["updated_at"] == now.isoformat()
    assert serialized["messages"][0]["id"] == "64f000000000000000000002"


def test_chat_write_guard_blocks_proxy_sessions():
    with pytest.raises(HTTPException) as exc:
        _ensure_chat_write_allowed({"id": "user-1", "proxy_by": "admin-1"})

    assert exc.value.status_code == 403
