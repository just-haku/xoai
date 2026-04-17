"""Role-aware prompt evolution candidate tracking and version lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from difflib import unified_diff
from typing import Any

from bson import ObjectId

from xoai.agents.prompt_bench import benchmark_prompt_candidate, get_prompt_benchmarks
from xoai.db.mongo import get_db
from xoai.prompts.manager import get_prompt_source

PROMOTION_BENCHMARK_THRESHOLD = 0.6


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _prompt_name_for_role(role: str) -> str:
    return {
        "architect": "architect",
        "executor": "executor",
        "supervisor": "supervisor",
        "user_agent": "user_agent",
    }.get(role, role)


def _proposed_prompt_content(role: str, lesson_statement: str) -> str:
    base = get_prompt_source(_prompt_name_for_role(role))
    candidate_tail = (
        "\n\n# Evolution Candidate\n"
        f"- Incorporate this operational lesson: {lesson_statement}\n"
        "- Preserve existing safety and role boundaries while improving the behavior above."
    )
    return (base + candidate_tail).strip()


async def record_prompt_candidate(
    *,
    role: str,
    profile_key: str,
    source_run_id: str,
    lesson_statement: str,
) -> None:
    """Record a candidate prompt adjustment for later replay/evaluation."""
    db = get_db()
    prompt_name = _prompt_name_for_role(role)
    current_content = get_prompt_source(prompt_name)
    await db.prompt_variants.insert_one(
        {
            "role": role,
            "prompt_name": prompt_name,
            "profile_key": profile_key,
            "source_run_id": source_run_id,
            "mutation_reason": lesson_statement,
            "current_prompt_content": current_content,
            "proposed_prompt_content": _proposed_prompt_content(role, lesson_statement),
            "promotion_status": "candidate",
            "evaluation_score": None,
            "evaluation_summary": None,
            "latest_benchmark_score": None,
            "latest_benchmark_summary": None,
            "recommended_model": None,
            "created_at": _now(),
        }
    )


async def evaluate_prompt_candidate(candidate_id: str) -> dict[str, Any]:
    """Evaluate a prompt candidate against its source run and profile history."""
    db = get_db()
    candidate = await db.prompt_variants.find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise ValueError("Prompt candidate not found.")

    source_run = await db.query_runs.find_one({"query_id": candidate["source_run_id"]})
    profile = await db.experience_profiles.find_one({"profile_key": candidate["profile_key"]}) or {}

    success_count = profile.get("success_count", 0)
    failure_count = profile.get("failure_count", 0)
    total = max(success_count + failure_count, 1)
    failure_pressure = failure_count / total
    source_quality = float((source_run or {}).get("quality_score", 0.0) or 0.0)
    benchmark_bonus = float(candidate.get("latest_benchmark_score") or 0.0)

    score = round(
        min(1.0, 0.25 + (failure_pressure * 0.35) + ((1.0 - source_quality) * 0.15) + (benchmark_bonus * 0.25)),
        3,
    )
    summary = (
        f"Profile failure pressure={failure_pressure:.2f}; source quality={source_quality:.2f}; "
        f"benchmark bonus={benchmark_bonus:.2f}. Candidate is {'promotion-ready' if benchmark_bonus >= PROMOTION_BENCHMARK_THRESHOLD else 'awaiting stronger replay evidence'}."
    )

    evaluation = {
        "candidate_id": candidate_id,
        "role": candidate["role"],
        "profile_key": candidate["profile_key"],
        "score": score,
        "summary": summary,
        "created_at": _now(),
    }
    await db.prompt_evaluations.insert_one(evaluation)
    await db.prompt_variants.update_one(
        {"_id": ObjectId(candidate_id)},
        {
            "$set": {
                "evaluation_score": score,
                "evaluation_summary": summary,
                "promotion_status": "evaluated",
                "evaluated_at": _now(),
            }
        },
    )
    return evaluation


async def set_prompt_candidate_status(candidate_id: str, status: str) -> dict[str, Any]:
    """Promote or reject a prompt candidate."""
    if status not in {"promoted", "rejected"}:
        raise ValueError("Unsupported prompt candidate status.")

    db = get_db()
    candidate = await db.prompt_variants.find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise ValueError("Prompt candidate not found.")

    now = _now()
    if status == "promoted":
        latest_benchmark_score = float(candidate.get("latest_benchmark_score") or 0.0)
        if latest_benchmark_score < PROMOTION_BENCHMARK_THRESHOLD:
            raise ValueError("Prompt candidate cannot be promoted before benchmark passes.")

        version_record = await _promote_to_prompt_version(candidate, now)
        await db.prompt_promotions.insert_one(
            {
                "candidate_id": candidate_id,
                "role": candidate["role"],
                "profile_key": candidate["profile_key"],
                "mutation_reason": candidate["mutation_reason"],
                "evaluation_score": candidate.get("evaluation_score"),
                "benchmark_score": candidate.get("latest_benchmark_score"),
                "recommended_model": candidate.get("recommended_model"),
                "prompt_version_id": version_record["id"],
                "created_at": now,
            }
        )

    await db.prompt_variants.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {"promotion_status": status, f"{status}_at": now}},
    )
    return {"candidate_id": candidate_id, "status": status, "updated_at": now}


async def run_prompt_candidate_benchmark(candidate_id: str) -> dict[str, Any]:
    db = get_db()
    candidate = await db.prompt_variants.find_one({"_id": ObjectId(candidate_id)})
    if not candidate:
        raise ValueError("Prompt candidate not found.")

    result = await benchmark_prompt_candidate(candidate)
    await db.prompt_variants.update_one(
        {"_id": ObjectId(candidate_id)},
        {
            "$set": {
                "latest_benchmark_score": result["aggregate_score"],
                "latest_benchmark_summary": result["baseline_comparison_summary"],
                "recommended_model": result.get("recommended_model"),
                "latest_model_benchmark_results": result.get("model_benchmark_results", []),
                "benchmarked_at": _now(),
                "promotion_status": "benchmarked",
            }
        },
    )
    return result


async def list_prompt_versions(limit: int = 100) -> list[dict[str, Any]]:
    db = get_db()
    docs = await db.prompt_versions.find({}).sort([("role", 1), ("version", -1)]).limit(limit).to_list(limit)
    return [_serialize_version(doc) for doc in docs]


async def get_prompt_version_detail(version_id: str) -> dict[str, Any]:
    db = get_db()
    version = await db.prompt_versions.find_one({"_id": ObjectId(version_id)})
    if not version:
        raise ValueError("Prompt version not found.")

    parent = None
    if version.get("parent_version"):
        parent = await db.prompt_versions.find_one({"_id": ObjectId(version["parent_version"])})

    serialized = _serialize_version(version)
    serialized["diff"] = _diff_prompt_contents(
        (parent or {}).get("content", ""),
        version.get("content", ""),
        from_label=(parent or {}).get("version_label", "parent"),
        to_label=version.get("version_label", "current"),
    )
    if parent:
        serialized["parent"] = _serialize_version(parent)
    return serialized


async def rollback_prompt_version(version_id: str) -> dict[str, Any]:
    db = get_db()
    target = await db.prompt_versions.find_one({"_id": ObjectId(version_id)})
    if not target:
        raise ValueError("Prompt version not found.")

    role = target["role"]
    active = await db.prompt_versions.find_one({"role": role, "status": "active"}, sort=[("version", -1)])
    now = _now()
    if active:
        await db.prompt_versions.update_one({"_id": active["_id"]}, {"$set": {"status": "rolled_back", "updated_at": now}})

    await db.prompt_versions.update_one({"_id": target["_id"]}, {"$set": {"status": "active", "updated_at": now}})
    return {"status": "active", "version_id": version_id, "role": role, "updated_at": now}


async def get_candidate_benchmarks(candidate_id: str, limit: int = 20) -> list[dict[str, Any]]:
    return await get_prompt_benchmarks(candidate_id, limit=limit)


async def _promote_to_prompt_version(candidate: dict[str, Any], now: datetime) -> dict[str, Any]:
    db = get_db()
    role = candidate["role"]
    active = await db.prompt_versions.find_one({"role": role, "status": "active"}, sort=[("version", -1)])
    next_version = int((active or {}).get("version", 0)) + 1
    if active:
        await db.prompt_versions.update_one({"_id": active["_id"]}, {"$set": {"status": "archived", "updated_at": now}})

    doc = {
        "role": role,
        "version": next_version,
        "version_label": f"v{next_version}",
        "content": candidate.get("proposed_prompt_content") or candidate.get("current_prompt_content") or "",
        "source_candidate_id": str(candidate["_id"]),
        "mutation_reason": candidate["mutation_reason"],
        "parent_version": str(active["_id"]) if active else None,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.prompt_versions.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return doc


def _serialize_version(doc: dict[str, Any]) -> dict[str, Any]:
    payload = dict(doc)
    payload["id"] = str(payload.pop("_id"))
    return payload


def _diff_prompt_contents(before: str, after: str, *, from_label: str, to_label: str) -> str:
    return "\n".join(
        unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=from_label,
            tofile=to_label,
            lineterm="",
        )
    )
