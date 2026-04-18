from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from xoai.metrics import metrics
from xoai.config import settings

logger = logging.getLogger("xoai.jobs")

JobHandler = Callable[[dict], Awaitable[None]]


class JobManager:
    def __init__(self):
        self._handlers: dict[str, JobHandler] = {}
        self._tasks: set[asyncio.Task] = set()

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    async def enqueue(
        self,
        job_type: str,
        payload: dict,
        *,
        max_attempts: int = 3,
        run_after: datetime | None = None,
        jitter_seconds: int = 0,
    ) -> str:
        from xoai.db.mongo import get_db

        db = get_db()
        now = datetime.now(timezone.utc)
        effective_run_after = run_after or now
        if jitter_seconds > 0:
            effective_run_after = effective_run_after + timedelta(seconds=random.randint(0, jitter_seconds))
        doc = {
            "type": job_type,
            "status": "queued",
            "attempts": 0,
            "max_attempts": max_attempts,
            "payload": payload,
            "last_error": None,
            "created_at": now,
            "updated_at": now,
            "run_after": effective_run_after,
        }
        result = await db.jobs.insert_one(doc)
        return str(result.inserted_id)

    def track_task(self, task: asyncio.Task) -> None:
        self._tasks.add(task)

        def _cleanup(done: asyncio.Task) -> None:
            self._tasks.discard(done)

        task.add_done_callback(_cleanup)

    async def drain(self) -> None:
        if not self._tasks:
            return
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*list(self._tasks), return_exceptions=True)
        self._tasks.clear()

    async def process_pending(self, limit: int = 25) -> None:
        from xoai.db.mongo import get_db

        db = get_db()
        now = datetime.now(timezone.utc)
        jobs = await db.jobs.find(
            {
                "status": {"$in": ["queued", "retry"]},
                "run_after": {"$lte": now},
            }
        ).sort("created_at", 1).limit(limit).to_list(limit)

        for job in jobs:
            task = asyncio.create_task(self._run_job(job))
            self.track_task(task)

    async def _run_job(self, job: dict) -> None:
        from xoai.db.mongo import get_db

        db = get_db()
        job_id = job["_id"]
        handler = self._handlers.get(job["type"])
        if handler is None:
            await db.jobs.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "last_error": f"No job handler registered for {job['type']}",
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            return

        await db.jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "running", "updated_at": datetime.now(timezone.utc)}, "$inc": {"attempts": 1}},
        )

        jitter = int(job.get("payload", {}).get("startup_jitter_seconds") or 0)
        if jitter:
            await asyncio.sleep(random.uniform(0, min(jitter, settings.restart_jitter_seconds)))

        try:
            await handler(job["payload"])
        except Exception as exc:
            metrics.incr("jobs.failed")
            logger.exception("Background job failed", extra={"job_id": str(job_id), "job_type": job["type"]})
            attempts = int(job.get("attempts", 0)) + 1
            status = "failed" if attempts >= job.get("max_attempts", 3) else "retry"
            run_after = datetime.now(timezone.utc) + timedelta(seconds=min(30, 5 * attempts))
            await db.jobs.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": status,
                        "last_error": str(exc),
                        "updated_at": datetime.now(timezone.utc),
                        "run_after": run_after,
                    }
                },
            )
            return

        metrics.incr("jobs.completed")
        await db.jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": "completed", "updated_at": datetime.now(timezone.utc), "last_error": None}},
        )


job_manager = JobManager()


async def process_due_jobs_once(limit: int = 25) -> None:
    await job_manager.process_pending(limit=limit)
