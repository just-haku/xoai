"""Scheduler service — CRUD for scheduled tasks and task run history."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from xoai.db.mongo import get_db

logger = logging.getLogger("xoai.scheduler.service")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def list_scheduled_tasks(limit: int = 100) -> list[dict]:
    db = get_db()
    docs = await db.scheduled_tasks.find({}).sort("created_at", -1).limit(limit).to_list(limit)
    return docs


async def get_scheduled_task(task_id: str) -> dict:
    db = get_db()
    doc = await db.scheduled_tasks.find_one({"_id": ObjectId(task_id)})
    if not doc:
        raise HTTPException(404, "Scheduled task not found")
    return doc


async def create_scheduled_task(data: dict, owner_user_id: str) -> dict:
    db = get_db()
    now = _now()
    doc = {
        "name": data["name"],
        "owner_user_id": owner_user_id,
        "cron": data["cron"],
        "timezone": data.get("timezone", "UTC"),
        "enabled": data.get("enabled", True),
        "agent_key": data["agent_key"],
        "workspace_scope": data.get("workspace_scope"),
        "tool_policy": data.get("tool_policy", {}),
        "payload": data.get("payload", {}),
        "last_run_at": None,
        "next_run_at": None,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.scheduled_tasks.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def update_scheduled_task(task_id: str, data: dict) -> dict:
    db = get_db()
    update_fields = {
        "updated_at": _now(),
    }
    for key in ("name", "cron", "timezone", "enabled", "agent_key", "workspace_scope", "tool_policy", "payload"):
        if key in data:
            update_fields[key] = data[key]

    result = await db.scheduled_tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Scheduled task not found")
    return await get_scheduled_task(task_id)


async def delete_scheduled_task(task_id: str) -> None:
    db = get_db()
    result = await db.scheduled_tasks.delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Scheduled task not found")


async def list_task_runs(task_id: str, limit: int = 50) -> list[dict]:
    db = get_db()
    docs = await db.task_runs.find(
        {"scheduled_task_id": task_id}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return docs


async def toggle_scheduled_task(task_id: str, enabled: bool) -> dict:
    db = get_db()
    result = await db.scheduled_tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"enabled": enabled, "updated_at": _now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Scheduled task not found")
    return await get_scheduled_task(task_id)
