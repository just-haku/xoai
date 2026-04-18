from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from xoai.config import settings
from xoai.db.mongo import get_db

logger = logging.getLogger("xoai.storage_gc")

TRANSIENT_RETENTION_CLASSES = {"sandbox_scratch", "upload_chunk", "raw_conversion"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def track_storage_artifact(
    *,
    user_id: str,
    path: str,
    artifact_type: str,
    retention_class: str,
    job_id: str | None = None,
    pinned: bool = False,
    expires_at: datetime | None = None,
) -> None:
    db = get_db()
    expiry = expires_at
    if not expiry and retention_class in TRANSIENT_RETENTION_CLASSES:
        expiry = _now() + timedelta(days=settings.transient_file_ttl_days)
    await db.storage_artifacts.update_one(
        {"user_id": user_id, "path": path},
        {
            "$set": {
                "artifact_type": artifact_type,
                "retention_class": retention_class,
                "job_id": job_id,
                "pinned": pinned,
                "expires_at": expiry,
                "updated_at": _now(),
            },
            "$setOnInsert": {
                "user_id": user_id,
                "path": path,
                "created_at": _now(),
            },
        },
        upsert=True,
    )


async def untrack_storage_artifact(user_id: str, path: str) -> None:
    db = get_db()
    await db.storage_artifacts.delete_one({"user_id": user_id, "path": path})


async def run_storage_gc(*, dry_run: bool = False, limit: int | None = None) -> dict:
    db = get_db()
    now = _now()
    batch_limit = limit or settings.gc_batch_size
    cursor = db.storage_artifacts.find(
        {
            "retention_class": {"$in": list(TRANSIENT_RETENTION_CLASSES)},
            "pinned": {"$ne": True},
            "expires_at": {"$lte": now},
        }
    ).sort("expires_at", 1).limit(batch_limit)
    docs = await cursor.to_list(batch_limit)
    deleted = []
    skipped = []

    for doc in docs:
        path = doc["path"]
        if await db.jobs.count_documents({"_id": doc.get("job_id"), "status": {"$in": ["queued", "running", "retry"]}}):
            skipped.append({"path": path, "reason": "active_job"})
            continue
        if not os.path.exists(path):
            if not dry_run:
                await db.storage_artifacts.delete_one({"_id": doc["_id"]})
            deleted.append({"path": path, "missing": True})
            continue
        if dry_run:
            deleted.append({"path": path, "dry_run": True})
            continue
        try:
            if os.path.isdir(path):
                import shutil

                shutil.rmtree(path)
            else:
                os.remove(path)
            await db.storage_artifacts.delete_one({"_id": doc["_id"]})
            deleted.append({"path": path})
        except Exception as exc:
            logger.warning("Failed to delete transient artifact", extra={"path": path, "error": str(exc)})
            skipped.append({"path": path, "reason": str(exc)})

    return {
        "scanned": len(docs),
        "deleted": deleted,
        "skipped": skipped,
        "dry_run": dry_run,
    }
