"""Execution run persistence and experience extraction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from xoai.agents.experience_consolidator import consolidate_new_lesson
from xoai.agents.evolution import record_prompt_candidate
from xoai.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def start_query_run(
    *,
    user: dict,
    conversation_id: str,
    channel: str,
    query: str,
    plan: dict[str, Any],
) -> str:
    db = get_db()
    query_id = str(uuid4())
    await db.query_runs.insert_one(
        {
            "query_id": query_id,
            "conversation_id": conversation_id,
            "user_id": user["id"],
            "user_role": user.get("role", "user"),
            "channel": channel,
            "input": query,
            "intent_profile": plan["intent_profile"],
            "topology_type": plan["topology_type"],
            "execution_plan": plan,
            "node_runs": [],
            "status": "running",
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    return query_id


async def record_node_start(query_id: str, node: dict[str, Any], node_input: str) -> None:
    db = get_db()
    node_run = {
        "node_id": node["id"],
        "role": node["role"],
        "action": node["action"],
        "branch_type": node.get("branch_type", "primary"),
        "parallel_group": node.get("parallel_group"),
        "retry_of": node.get("retry_of"),
        "verifier_for": node.get("verifier_for"),
        "max_retries": node.get("max_retries", 0),
        "entry_condition": node.get("entry_condition"),
        "depends_on": node.get("depends_on", []),
        "metadata": node.get("metadata", {}),
        "status": "running",
        "input": node_input,
        "output": "",
        "output_chunks": [],
        "tool_events": [],
        "error": None,
        "started_at": _now(),
        "updated_at": _now(),
    }
    await db.query_runs.update_one(
        {"query_id": query_id},
        {"$push": {"node_runs": node_run}, "$set": {"updated_at": _now()}},
    )


async def append_node_event(query_id: str, node_id: str, event: dict[str, Any]) -> None:
    db = get_db()
    stamped_event = {**event, "timestamp": event.get("timestamp") or _now()}

    if stamped_event["type"] == "content":
        await db.query_runs.update_one(
            {"query_id": query_id, "node_runs.node_id": node_id},
            {
                "$set": {
                    "node_runs.$.updated_at": _now(),
                    "updated_at": _now(),
                },
                "$push": {"node_runs.$.output_chunks": stamped_event.get("content", "")},
            },
        )
        return

    if stamped_event["type"] in {"tool_start", "tool_end"}:
        await db.query_runs.update_one(
            {"query_id": query_id, "node_runs.node_id": node_id},
            {
                "$set": {
                    "node_runs.$.updated_at": _now(),
                    "updated_at": _now(),
                },
                "$push": {"node_runs.$.tool_events": stamped_event},
            },
        )
        return

    if stamped_event["type"] == "error":
        await db.query_runs.update_one(
            {"query_id": query_id, "node_runs.node_id": node_id},
            {
                "$set": {
                    "node_runs.$.error": stamped_event.get("message"),
                    "node_runs.$.updated_at": _now(),
                    "updated_at": _now(),
                }
            },
        )


async def complete_node(
    query_id: str,
    node_id: str,
    output: str,
    status: str = "completed",
    structured_output: dict[str, Any] | None = None,
) -> None:
    db = get_db()
    set_fields = {
        "node_runs.$.status": status,
        "node_runs.$.output": output,
        "node_runs.$.completed_at": _now(),
        "node_runs.$.updated_at": _now(),
        "updated_at": _now(),
    }
    if structured_output is not None:
        set_fields["node_runs.$.structured_output"] = structured_output

    await db.query_runs.update_one(
        {"query_id": query_id, "node_runs.node_id": node_id},
        {"$set": set_fields},
    )


async def finalize_query_run(
    *,
    query_id: str,
    final_output: str,
    status: str,
    failure_reason: str | None = None,
) -> None:
    db = get_db()
    run = await db.query_runs.find_one({"query_id": query_id})
    if not run:
        return

    quality_score = 1.0 if status == "completed" and final_output.strip() else 0.0
    failure_modes = [failure_reason] if failure_reason else []

    await db.query_runs.update_one(
        {"query_id": query_id},
        {
            "$set": {
                "status": status,
                "final_output": final_output,
                "failure_modes": failure_modes,
                "quality_score": quality_score,
                "completed_at": _now(),
                "updated_at": _now(),
            }
        },
    )

    await _extract_experience(run | {"final_output": final_output, "status": status, "failure_modes": failure_modes})


async def lookup_experience(profile_key: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    db = get_db()
    cursor = db.experience_lessons.find(
        {"profile_key": profile_key, "keep_state": "keep"}
    ).sort("utility_score", -1).limit(limit)
    lessons = await cursor.to_list(limit)
    for lesson in lessons:
        lesson["id"] = str(lesson.pop("_id"))
    return lessons


async def _extract_experience(run: dict[str, Any]) -> None:
    db = get_db()
    profile_key = run.get("intent_profile", "unknown")
    success = run.get("status") == "completed" and bool(run.get("final_output", "").strip())
    failure_modes = run.get("failure_modes") or ["unknown failure"]

    lesson_statement = (
        f"Topology '{run.get('topology_type')}' completed successfully for profile '{profile_key}'."
        if success
        else f"Topology '{run.get('topology_type')}' failed for profile '{profile_key}' with {failure_modes}."
    )
    utility_components = _build_utility_components(run, success)

    lesson_doc = {
        "profile_key": profile_key,
        "query_id": run["query_id"],
        "topology_type": run.get("topology_type"),
        "lesson_type": "success_pattern" if success else "failure_pattern",
        "statement": lesson_statement,
        "confidence": utility_components["confidence"],
        "utility_score": utility_components["utility_score"],
        "utility_components": utility_components,
        "severity": utility_components["severity"],
        "keep_state": "keep",
        "created_at": _now(),
        "updated_at": _now(),
    }
    await consolidate_new_lesson(lesson_doc)

    await db.experience_profiles.update_one(
        {"profile_key": profile_key},
        {
            "$setOnInsert": {"profile_key": profile_key, "created_at": _now()},
            "$set": {"updated_at": _now()},
            "$inc": {
                "run_count": 1,
                "success_count": 1 if success else 0,
                "failure_count": 0 if success else 1,
            },
        },
        upsert=True,
    )

    if not success:
        first_role = (run.get("execution_plan", {}).get("nodes") or [{}])[0].get("role")
        if first_role:
            await record_prompt_candidate(
                role=first_role,
                profile_key=profile_key,
                source_run_id=run["query_id"],
                lesson_statement=lesson_statement,
            )


def _build_utility_components(run: dict[str, Any], success: bool) -> dict[str, float]:
    quality_score = float(run.get("quality_score") or 0.0)
    failure_modes = run.get("failure_modes") or []
    success_delta = round(quality_score if success else max(0.0, 1.0 - quality_score), 3)
    reuse_rate = round(min(1.0, max(1, len(run.get("node_runs", []))) / 5.0), 3)
    severity = round(min(1.0, 0.35 + (0.2 * len(failure_modes))) if not success else 0.2, 3)
    freshness = 1.0
    confidence = round(0.75 if success else 0.6, 3)
    utility_score = round(
        (success_delta * 0.35) +
        (reuse_rate * 0.15) +
        (severity * 0.2) +
        (freshness * 0.1) +
        (confidence * 0.2),
        3,
    )
    return {
        "success_delta": success_delta,
        "reuse_rate": reuse_rate,
        "severity": severity,
        "freshness": freshness,
        "confidence": confidence,
        "utility_score": utility_score,
    }
