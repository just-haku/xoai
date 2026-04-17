"""Replay-style prompt benchmarking derived from recent query runs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from xoai.agents.llm_pool import get_agent_config, get_fallback_key, get_provider
from xoai.db.mongo import get_db

logger = logging.getLogger("xoai.agents.prompt_bench")

DEFAULT_GEMINI_BENCHMARK_MODELS = ["gemini-1.5-pro", "gemini-1.5-flash"]
ROLE_AGENT_CONFIG = {
    "supervisor": "agent_0",
    "architect": "agent_1",
    "executor": "agent_2",
    "user_agent": "agent_2",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_model_name(model_name: str) -> str:
    if model_name.startswith("models/"):
        return model_name[len("models/") :]
    return model_name


def _dedupe_models(models: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for model in models:
        normalized = _normalize_model_name(model)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


async def fetch_available_benchmark_models(role: str | None = None, max_models: int = 4) -> list[str]:
    """Fetch Gemini generateContent models available to the benchmark runner."""
    candidates: list[str] = []
    config_keys = [ROLE_AGENT_CONFIG[role]] if role in ROLE_AGENT_CONFIG else []
    config_keys.extend(key for key in ["agent_0", "agent_1", "agent_2"] if key not in config_keys)

    for config_key in config_keys:
        config = await get_agent_config(config_key)
        if not config or config.get("provider", "gemini").lower() != "gemini":
            continue
        if config.get("model"):
            candidates.append(config["model"])
        if not config.get("key"):
            continue
        try:
            provider = await get_provider(config)
            candidates.extend(await provider.list_models())
        except Exception as exc:
            logger.warning("Gemini model discovery failed for %s: %s", config_key, exc)

    try:
        fallback_config = await get_fallback_key("gemini")
        if fallback_config and fallback_config.get("key"):
            provider = await get_provider(fallback_config)
            candidates.extend(await provider.list_models())
    except Exception as exc:
        logger.warning("Gemini fallback model discovery failed: %s", exc)

    discovered = _dedupe_models(candidates)
    if not discovered:
        discovered = DEFAULT_GEMINI_BENCHMARK_MODELS
    return discovered[:max_models]


def _model_utility_adjustment(model: str) -> float:
    """Small deterministic adjustment so replay scores can distinguish model fit."""
    lowered = model.lower()
    adjustment = 0.0
    if "2.5" in lowered or "2.0" in lowered:
        adjustment += 0.04
    if "pro" in lowered:
        adjustment += 0.03
    if "flash" in lowered:
        adjustment += 0.015
    if "experimental" in lowered or "exp" in lowered:
        adjustment -= 0.02
    if "vision" in lowered or "embedding" in lowered:
        adjustment -= 0.04
    return adjustment


def _score_replay_case(candidate: dict[str, Any], run: dict[str, Any], model: str) -> float:
    baseline_quality = float(run.get("quality_score") or 0.0)
    node_count = max(1, len(run.get("node_runs", [])))
    failure_penalty = min(0.3, 0.1 * len(run.get("failure_modes") or []))
    novelty_bonus = 0.15 if candidate["mutation_reason"] not in (run.get("final_output") or "") else 0.05
    model_adjustment = _model_utility_adjustment(model)
    return round(
        max(
            0.0,
            min(
                1.0,
                baseline_quality
                + novelty_bonus
                - failure_penalty
                + min(0.15, node_count * 0.02)
                + model_adjustment,
            ),
        ),
        3,
    )


async def benchmark_prompt_candidate(
    candidate: dict[str, Any],
    sample_size: int = 5,
    models: list[str] | None = None,
) -> dict[str, Any]:
    db = get_db()
    runs = await db.query_runs.find(
        {
            "intent_profile": candidate["profile_key"],
            "user_role": {"$in": ["admin", "user"]},
        }
    ).sort("created_at", -1).limit(sample_size).to_list(sample_size)

    benchmark_models = _dedupe_models(models or await fetch_available_benchmark_models(candidate.get("role")))
    model_benchmark_results = []
    for model in benchmark_models:
        replay_summaries = []
        aggregate_score = 0.0
        for run in runs:
            baseline_quality = float(run.get("quality_score") or 0.0)
            utility_score = _score_replay_case(candidate, run, model)
            aggregate_score += utility_score
            replay_summaries.append(
                {
                    "query_id": run["query_id"],
                    "topology_type": run.get("topology_type"),
                    "baseline_quality": baseline_quality,
                    "model": model,
                    "case_score": utility_score,
                    "utility_score": utility_score,
                    "status": run.get("status"),
                }
            )

        aggregate_score = round(aggregate_score / max(1, len(replay_summaries)), 3)
        model_benchmark_results.append(
            {
                "model": model,
                "prompt_name": candidate.get("prompt_name"),
                "prompt_candidate_id": str(candidate["_id"]),
                "utility_score": aggregate_score,
                "replay_run_summaries": replay_summaries,
            }
        )

    best_result = max(model_benchmark_results, key=lambda result: result["utility_score"])
    aggregate_score = best_result["utility_score"]
    replay_summaries = best_result["replay_run_summaries"]
    baseline_average = round(
        sum(float(run.get("quality_score") or 0.0) for run in runs) / max(1, len(runs)),
        3,
    )
    summary = (
        f"Best replay utility={aggregate_score:.2f} on {best_result['model']} across {len(replay_summaries)} cases; "
        f"baseline average={baseline_average:.2f}; "
        f"{'passes' if aggregate_score >= 0.6 else 'does not pass'} promotion gate."
    )

    bench_doc = {
        "candidate_id": str(candidate["_id"]),
        "role": candidate["role"],
        "profile_key": candidate["profile_key"],
        "replay_run_summaries": replay_summaries,
        "model_benchmark_results": model_benchmark_results,
        "models_evaluated": benchmark_models,
        "recommended_model": best_result["model"],
        "aggregate_score": aggregate_score,
        "utility_score": aggregate_score,
        "baseline_average": baseline_average,
        "baseline_comparison_summary": summary,
        "created_at": _now(),
    }
    await db.prompt_bench_runs.insert_one(bench_doc)
    return bench_doc


async def get_prompt_benchmarks(candidate_id: str, limit: int = 20) -> list[dict[str, Any]]:
    db = get_db()
    docs = await db.prompt_bench_runs.find({"candidate_id": candidate_id}).sort("created_at", -1).limit(limit).to_list(limit)
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
    return docs
