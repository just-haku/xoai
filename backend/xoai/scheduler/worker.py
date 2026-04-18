"""Chronos — Persistent scheduler tick worker.

Runs a 60-second background loop that evaluates cron expressions for
active scheduled tasks and dispatches due tasks to the Agent Runtime.

Locking: Uses a MongoDB atomic lease to prevent double-execution in
multi-instance deployments.

Lifecycle: Wired into FastAPI lifespan via start_scheduler() / stop_scheduler().
"""

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timezone

from croniter import croniter

from xoai.db.mongo import get_db

logger = logging.getLogger("xoai.scheduler.worker")

TICK_INTERVAL_SECONDS = 60
LEASE_TTL_SECONDS = 300  # 5-minute max lease per task execution

_worker_task: asyncio.Task | None = None
_shutdown_event = asyncio.Event()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_valid_cron(expression: str) -> bool:
    """Validate a cron expression without throwing."""
    try:
        croniter(expression)
        return True
    except (ValueError, KeyError, TypeError):
        return False


def _is_due(cron_expr: str, last_run_at: datetime | None) -> bool:
    """Check if a cron-scheduled task is due for execution.

    A task is due if the most recent trigger time (looking back from now)
    is after the last recorded run time.
    """
    now = _now_utc()
    try:
        cron = croniter(cron_expr, now)
        prev_fire = cron.get_prev(datetime).replace(tzinfo=timezone.utc)

        if last_run_at is None:
            return True

        # Ensure last_run_at is tz-aware
        if last_run_at.tzinfo is None:
            last_run_at = last_run_at.replace(tzinfo=timezone.utc)

        return prev_fire > last_run_at
    except Exception as exc:
        logger.warning("Cron evaluation failed for '%s': %s", cron_expr, exc)
        return False


def _next_fire(cron_expr: str) -> datetime | None:
    """Compute the next fire time for a cron expression."""
    try:
        cron = croniter(cron_expr, _now_utc())
        return cron.get_next(datetime).replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def _acquire_lease(db, task_id: str, lease_id: str) -> bool:
    """Atomically acquire an execution lease to prevent double-dispatch.

    Uses a findAndModify pattern: only succeed if no active lease exists
    or the existing lease has expired.
    """
    now = _now_utc()
    result = await db.scheduler_leases.find_one_and_update(
        {
            "task_id": task_id,
            "$or": [
                {"lease_id": None},
                {"expires_at": {"$lt": now}},
            ],
        },
        {
            "$set": {
                "lease_id": lease_id,
                "acquired_at": now,
                "expires_at": datetime(
                    now.year, now.month, now.day,
                    now.hour, now.minute, now.second,
                    tzinfo=timezone.utc,
                ),
            },
            "$setOnInsert": {"task_id": task_id},
        },
        upsert=True,
        return_document=True,
    )
    # We acquired it if the returned doc has our lease_id
    return result is not None and result.get("lease_id") == lease_id


async def _release_lease(db, task_id: str, lease_id: str) -> None:
    """Release an execution lease after completion."""
    await db.scheduler_leases.update_one(
        {"task_id": task_id, "lease_id": lease_id},
        {"$set": {"lease_id": None, "expires_at": None}},
    )


async def _dispatch_task(task: dict) -> dict:
    """Dispatch a scheduled task to the Agent Runtime for execution.

    Returns a run result dict with status and output.
    """
    from xoai.agents.llm_pool import llm_pool

    agent_key = task.get("agent_key", "agent_0")
    payload = task.get("payload", {})
    prompt = payload.get("prompt", "")

    if not prompt:
        return {
            "status": "skipped",
            "output": "No prompt defined in task payload",
        }

    try:
        result = await llm_pool.generate(prompt)
        return {
            "status": "success",
            "output": result[:5000] if result else "",
        }
    except Exception as exc:
        return {
            "status": "error",
            "output": f"{type(exc).__name__}: {str(exc)[:1000]}",
        }


async def _record_run(db, task: dict, run_result: dict) -> None:
    """Log the task execution result to the task_runs collection."""
    task_id = str(task["_id"])
    now = _now_utc()

    run_doc = {
        "scheduled_task_id": task_id,
        "task_name": task.get("name", ""),
        "agent_key": task.get("agent_key", ""),
        "status": run_result.get("status", "unknown"),
        "output": run_result.get("output", ""),
        "created_at": now,
        "duration_ms": 0,  # TODO: measure actual duration
    }
    await db.task_runs.insert_one(run_doc)

    # Update the task's last_run_at and next_run_at
    next_fire = _next_fire(task.get("cron", ""))
    await db.scheduled_tasks.update_one(
        {"_id": task["_id"]},
        {
            "$set": {
                "last_run_at": now,
                "next_run_at": next_fire,
                "updated_at": now,
            }
        },
    )


async def _tick() -> None:
    """Single scheduler tick: find and execute all due tasks."""
    db = get_db()

    # Query for enabled tasks
    tasks = await db.scheduled_tasks.find(
        {"enabled": True}
    ).to_list(200)

    if not tasks:
        return

    for task in tasks:
        cron_expr = task.get("cron", "")
        if not cron_expr or not is_valid_cron(cron_expr):
            continue

        if not _is_due(cron_expr, task.get("last_run_at")):
            continue

        task_id = str(task["_id"])
        lease_id = uuid.uuid4().hex

        # Acquire execution lock
        if not await _acquire_lease(db, task_id, lease_id):
            logger.debug("Lease not acquired for task %s, skipping (another instance running)", task_id)
            continue

        logger.info("Dispatching scheduled task: %s (%s)", task.get("name"), task_id)

        try:
            run_result = await _dispatch_task(task)
            await _record_run(db, task, run_result)

            level = logging.INFO if run_result["status"] == "success" else logging.WARNING
            logger.log(level, "Task %s completed: %s", task_id, run_result["status"])

        except Exception as exc:
            logger.error("Task %s execution crashed: %s\n%s", task_id, exc, traceback.format_exc())
            await _record_run(db, task, {
                "status": "crash",
                "output": f"{type(exc).__name__}: {str(exc)[:1000]}",
            })

        finally:
            await _release_lease(db, task_id, lease_id)


async def _run_loop() -> None:
    """Persistent background loop — ticks every TICK_INTERVAL_SECONDS."""
    logger.info("Chronos scheduler worker started (tick=%ds)", TICK_INTERVAL_SECONDS)

    while not _shutdown_event.is_set():
        try:
            await _tick()
        except Exception as exc:
            logger.error("Scheduler tick failed: %s\n%s", exc, traceback.format_exc())

        # Wait for the interval or until shutdown is signaled
        try:
            await asyncio.wait_for(
                _shutdown_event.wait(),
                timeout=TICK_INTERVAL_SECONDS,
            )
            break  # Shutdown was signaled
        except asyncio.TimeoutError:
            pass  # Normal: timeout means we should tick again

    logger.info("Chronos scheduler worker stopped")


async def start_scheduler() -> None:
    """Start the scheduler background loop. Safe to call multiple times."""
    global _worker_task, _shutdown_event

    if _worker_task and not _worker_task.done():
        logger.warning("Scheduler already running; ignoring duplicate start")
        return

    _shutdown_event = asyncio.Event()
    _worker_task = asyncio.create_task(_run_loop())
    logger.info("Chronos scheduler task created")


async def stop_scheduler() -> None:
    """Gracefully stop the scheduler loop."""
    global _worker_task

    if not _worker_task:
        return

    _shutdown_event.set()

    try:
        await asyncio.wait_for(_worker_task, timeout=10.0)
    except asyncio.TimeoutError:
        logger.warning("Scheduler did not stop within 10s; cancelling")
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass

    _worker_task = None
    logger.info("Chronos scheduler shut down cleanly")
