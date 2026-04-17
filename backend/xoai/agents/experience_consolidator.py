"""Experience lesson consolidation engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from xoai.db.mongo import get_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_statement(statement: str) -> str:
    return " ".join(statement.lower().split())


async def consolidate_new_lesson(lesson_doc: dict[str, Any]) -> dict[str, Any]:
    """Add a new lesson or merge it into an existing compatible lesson."""
    db = get_db()
    normalized = normalize_statement(lesson_doc["statement"])
    profile_key = lesson_doc["profile_key"]

    existing = await db.experience_lessons.find_one(
        {
            "profile_key": profile_key,
            "lesson_type": lesson_doc["lesson_type"],
            "topology_type": lesson_doc.get("topology_type"),
            "normalized_statement": normalized,
            "keep_state": "keep",
        }
    )

    if not existing:
        lesson_doc["normalized_statement"] = normalized
        lesson_doc["occurrence_count"] = 1
        lesson_doc["source_run_ids"] = [lesson_doc["query_id"]]
        result = await db.experience_lessons.insert_one(lesson_doc)
        await _log_consolidation(
            profile_key=profile_key,
            action="add",
            source_lesson_id=str(result.inserted_id),
            target_lesson_id=None,
            metadata={"statement": lesson_doc["statement"]},
        )
        await recompute_profile_insights(profile_key)
        lesson_doc["id"] = str(result.inserted_id)
        return lesson_doc

    await db.experience_lessons.update_one(
        {"_id": existing["_id"]},
        {
            "$inc": {"occurrence_count": 1},
            "$max": {
                "confidence": lesson_doc.get("confidence", 0.0),
                "utility_score": lesson_doc.get("utility_score", 0.0),
            },
            "$addToSet": {"source_run_ids": lesson_doc["query_id"]},
            "$set": {"updated_at": _now()},
        },
    )
    await _log_consolidation(
        profile_key=profile_key,
        action="merge",
        source_lesson_id=None,
        target_lesson_id=str(existing["_id"]),
        metadata={"statement": lesson_doc["statement"], "mode": "auto"},
    )
    await recompute_profile_insights(profile_key)
    existing["id"] = str(existing["_id"])
    return existing


async def apply_consolidation_action(
    *,
    lesson_id: str,
    action: str,
    target_lesson_id: str | None = None,
) -> dict[str, Any]:
    """Apply a manual consolidation action to a lesson."""
    if action not in {"add", "keep", "prune", "merge"}:
        raise ValueError("Unsupported consolidation action.")

    db = get_db()
    source = await db.experience_lessons.find_one({"_id": ObjectId(lesson_id)})
    if not source:
        raise ValueError("Lesson not found.")

    profile_key = source["profile_key"]
    now = _now()

    if action in {"add", "keep"}:
        keep_state = "keep"
        await db.experience_lessons.update_one(
            {"_id": source["_id"]},
            {
                "$set": {
                    "keep_state": keep_state,
                    "merged_into": None,
                    "updated_at": now,
                }
            },
        )
        await _log_consolidation(
            profile_key=profile_key,
            action=action,
            source_lesson_id=lesson_id,
            target_lesson_id=None,
        )
    elif action == "prune":
        await db.experience_lessons.update_one(
            {"_id": source["_id"]},
            {"$set": {"keep_state": "pruned", "updated_at": now}},
        )
        await _log_consolidation(
            profile_key=profile_key,
            action="prune",
            source_lesson_id=lesson_id,
            target_lesson_id=None,
        )
    elif action == "merge":
        if not target_lesson_id or target_lesson_id == lesson_id:
            raise ValueError("A different target lesson is required for merge.")
        target = await db.experience_lessons.find_one({"_id": ObjectId(target_lesson_id)})
        if not target:
            raise ValueError("Target lesson not found.")
        if target["profile_key"] != profile_key:
            raise ValueError("Cannot merge lessons across different profiles.")

        merged_sources = list({
            *source.get("source_run_ids", []),
            *target.get("source_run_ids", []),
        })
        occurrence_count = int(source.get("occurrence_count", 1)) + int(target.get("occurrence_count", 1))
        utility_score = max(source.get("utility_score", 0.0), target.get("utility_score", 0.0))
        confidence = max(source.get("confidence", 0.0), target.get("confidence", 0.0))

        await db.experience_lessons.update_one(
            {"_id": target["_id"]},
            {
                "$set": {
                    "source_run_ids": merged_sources,
                    "occurrence_count": occurrence_count,
                    "utility_score": utility_score,
                    "confidence": confidence,
                    "updated_at": now,
                }
            },
        )
        await db.experience_lessons.update_one(
            {"_id": source["_id"]},
            {
                "$set": {
                    "keep_state": "merged",
                    "merged_into": target_lesson_id,
                    "updated_at": now,
                }
            },
        )
        await _log_consolidation(
            profile_key=profile_key,
            action="merge",
            source_lesson_id=lesson_id,
            target_lesson_id=target_lesson_id,
            metadata={"mode": "manual"},
        )

    await recompute_profile_insights(profile_key)
    updated = await db.experience_lessons.find_one({"_id": ObjectId(lesson_id)})
    updated["id"] = str(updated.pop("_id"))
    return updated


async def recompute_profile_insights(profile_key: str) -> None:
    """Rebuild profile insights from active kept lessons."""
    db = get_db()
    lessons = await db.experience_lessons.find(
        {"profile_key": profile_key, "keep_state": "keep"}
    ).sort("utility_score", -1).to_list(100)

    success_lessons = [lesson for lesson in lessons if lesson["lesson_type"] == "success_pattern"]
    failure_lessons = [lesson for lesson in lessons if lesson["lesson_type"] == "failure_pattern"]
    success_patterns = [lesson["statement"] for lesson in success_lessons[:5]]
    failure_patterns = [lesson["statement"] for lesson in failure_lessons[:5]]

    contrasts = []
    for success, failure in zip(success_lessons[:3], failure_lessons[:3]):
        contrasts.append(
            {
                "prefer": success["statement"],
                "avoid": failure["statement"],
                "utility_delta": round(success.get("utility_score", 0.0) - failure.get("utility_score", 0.0), 3),
            }
        )

    recommended = [lesson["statement"] for lesson in success_lessons[:3]]
    recommended.extend([f"Avoid: {item['statement']}" for item in failure_lessons[:2]])
    utility_components = _aggregate_utility_components(lessons)
    comparative_summary = _build_comparative_summary(success_lessons, failure_lessons)

    await db.experience_insights.update_one(
        {"profile_key": profile_key},
        {
            "$setOnInsert": {"profile_key": profile_key, "created_at": _now()},
            "$set": {
                "success_patterns": success_patterns,
                "failure_patterns": failure_patterns,
                "contrasts": contrasts,
                "recommended_behaviors": recommended,
                "comparative_summary": comparative_summary,
                "utility_components": utility_components,
                "utility_score": utility_components["utility_score"],
                "updated_at": _now(),
            },
        },
        upsert=True,
    )


async def list_consolidations(limit: int = 100) -> list[dict[str, Any]]:
    db = get_db()
    docs = await db.experience_consolidations.find({}).sort("created_at", -1).limit(limit).to_list(limit)
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
    return docs


async def _log_consolidation(
    *,
    profile_key: str,
    action: str,
    source_lesson_id: str | None,
    target_lesson_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db = get_db()
    await db.experience_consolidations.insert_one(
        {
            "profile_key": profile_key,
            "action": action,
            "source_lesson_id": source_lesson_id,
            "target_lesson_id": target_lesson_id,
            "metadata": metadata or {},
            "created_at": _now(),
        }
    )


def _aggregate_utility_components(lessons: list[dict[str, Any]]) -> dict[str, float]:
    if not lessons:
        return {
            "success_delta": 0.0,
            "reuse_rate": 0.0,
            "severity": 0.0,
            "freshness": 0.0,
            "confidence": 0.0,
            "utility_score": 0.0,
        }

    count = len(lessons)
    totals = {
        "success_delta": 0.0,
        "reuse_rate": 0.0,
        "severity": 0.0,
        "freshness": 0.0,
        "confidence": 0.0,
    }
    for lesson in lessons:
        components = lesson.get("utility_components") or {}
        for key in totals:
            totals[key] += float(components.get(key, lesson.get(key, 0.0)) or 0.0)

    averaged = {key: round(value / count, 3) for key, value in totals.items()}
    averaged["utility_score"] = round(
        (averaged["success_delta"] * 0.35) +
        (averaged["reuse_rate"] * 0.15) +
        (averaged["severity"] * 0.2) +
        (averaged["freshness"] * 0.1) +
        (averaged["confidence"] * 0.2),
        3,
    )
    return averaged


def _build_comparative_summary(success_lessons: list[dict[str, Any]], failure_lessons: list[dict[str, Any]]) -> dict[str, Any]:
    success_utility = round(sum(item.get("utility_score", 0.0) for item in success_lessons[:5]), 3)
    failure_utility = round(sum(item.get("utility_score", 0.0) for item in failure_lessons[:5]), 3)
    return {
        "success_count": len(success_lessons),
        "failure_count": len(failure_lessons),
        "success_utility": success_utility,
        "failure_utility": failure_utility,
        "utility_gap": round(success_utility - failure_utility, 3),
    }
