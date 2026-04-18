from __future__ import annotations

from datetime import datetime, timezone
from difflib import unified_diff
from pathlib import Path

from bson import ObjectId
from fastapi import HTTPException

from xoai.db.mongo import get_db
from xoai.prompts.manager import PROMPTS_DIR, get_prompt_source


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _prompt_disk_names() -> list[str]:
    return sorted(path.stem for path in Path(PROMPTS_DIR).glob("*.md"))


async def seed_prompt_versions_from_disk() -> int:
    db = get_db()
    created = 0
    for role in _prompt_disk_names():
        active = await db.prompt_versions.find_one({"role": role, "status": "active"})
        if active:
            continue
        content = get_prompt_source(role)
        if not content:
            continue
        await db.prompt_versions.insert_one(
            {
                "role": role,
                "version": 1,
                "version_label": "v1",
                "content": content,
                "source_candidate_id": None,
                "mutation_reason": "seeded_from_disk",
                "parent_version": None,
                "status": "active",
                "created_at": _now(),
                "updated_at": _now(),
            }
        )
        created += 1
    return created


async def list_prompt_families() -> list[dict]:
    db = get_db()
    roles = await db.prompt_versions.distinct("role")
    payload = []
    for role in sorted(roles):
        active = await db.prompt_versions.find_one({"role": role, "status": "active"}, sort=[("version", -1)])
        latest = await db.prompt_versions.find_one({"role": role}, sort=[("version", -1)])
        payload.append(
            {
                "role": role,
                "active_version_id": str(active["_id"]) if active else None,
                "active_version_label": active.get("version_label") if active else None,
                "latest_version": latest.get("version", 0) if latest else 0,
                "updated_at": (latest or {}).get("updated_at"),
            }
        )
    return payload


async def create_prompt_version(role: str, content: str, mutation_reason: str, author_id: str) -> dict:
    db = get_db()
    latest = await db.prompt_versions.find_one({"role": role}, sort=[("version", -1)])
    next_version = int((latest or {}).get("version", 0)) + 1
    doc = {
        "role": role,
        "version": next_version,
        "version_label": f"v{next_version}",
        "content": content,
        "source_candidate_id": None,
        "mutation_reason": mutation_reason,
        "parent_version": str(latest["_id"]) if latest else None,
        "status": "draft",
        "author_id": author_id,
        "created_at": _now(),
        "updated_at": _now(),
    }
    result = await db.prompt_versions.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return doc


async def activate_prompt_version(version_id: str) -> dict:
    db = get_db()
    version = await db.prompt_versions.find_one({"_id": ObjectId(version_id)})
    if not version:
        raise HTTPException(404, "Prompt version not found")
    now = _now()
    await db.prompt_versions.update_many(
        {"role": version["role"], "status": "active"},
        {"$set": {"status": "archived", "updated_at": now}},
    )
    await db.prompt_versions.update_one(
        {"_id": version["_id"]},
        {"$set": {"status": "active", "updated_at": now}},
    )
    version["status"] = "active"
    version["updated_at"] = now
    version["id"] = str(version["_id"])
    return version


async def prompt_diff(version_id: str) -> dict:
    db = get_db()
    version = await db.prompt_versions.find_one({"_id": ObjectId(version_id)})
    if not version:
        raise HTTPException(404, "Prompt version not found")
    parent = None
    if version.get("parent_version"):
        try:
            parent = await db.prompt_versions.find_one({"_id": ObjectId(version["parent_version"])})
        except Exception:
            parent = None
    diff = "\n".join(
        unified_diff(
            (parent or {}).get("content", "").splitlines(),
            version.get("content", "").splitlines(),
            fromfile=(parent or {}).get("version_label", "parent"),
            tofile=version.get("version_label", "current"),
            lineterm="",
        )
    )
    return {
        "id": str(version["_id"]),
        "role": version["role"],
        "version_label": version["version_label"],
        "diff": diff,
        "content": version.get("content", ""),
    }
