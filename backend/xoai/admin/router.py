"""Admin dashboard routes: settings CRUD, stats."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any

from bson import ObjectId
from xoai.auth.dependencies import require_admin
from xoai.admin import service
from xoai.agents.evolution import (
    evaluate_prompt_candidate,
    get_candidate_benchmarks,
    get_prompt_version_detail,
    list_prompt_versions,
    rollback_prompt_version,
    run_prompt_candidate_benchmark,
    set_prompt_candidate_status,
)
from xoai.agents.experience_consolidator import apply_consolidation_action, list_consolidations
from xoai.db.mongo import get_db

router = APIRouter()


class SettingUpdate(BaseModel):
    key: str
    value: dict


@router.get("/settings")
async def list_settings(_=Depends(require_admin)):
    """List all setting keys (values are encrypted, returned on individual get)."""
    return await service.list_setting_keys()


@router.get("/settings/{key}")
async def get_setting(key: str, _=Depends(require_admin)):
    val = await service.get_setting(key)
    if val is None:
        raise HTTPException(404, f"Setting '{key}' not found")
    return {"key": key, "value": val}


@router.put("/settings")
async def set_setting(req: SettingUpdate, _=Depends(require_admin)):
    await service.set_setting(req.key, req.value)
    return {"message": f"Setting '{req.key}' saved"}

class ModelFetchReq(BaseModel):
    provider: str
    key: str
    base_url: Optional[str] = None

@router.post("/settings/intelligence/models")
async def fetch_admin_agent_models(req: ModelFetchReq, _=Depends(require_admin)):
    """Fetch available models for a global agent using unsaved keys."""
    from xoai.agents.llm_pool import get_provider
    from fastapi import HTTPException
    try:
        provider = await get_provider({
            "provider": req.provider,
            "key": req.key,
            "base_url": req.base_url
        })
        models = await provider.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch models: {str(e)}")


@router.delete("/settings/{key}")
async def delete_setting(key: str, _=Depends(require_admin)):
    ok = await service.delete_setting(key)
    if not ok:
        raise HTTPException(404, f"Setting '{key}' not found")
    return {"message": f"Setting '{key}' deleted"}


@router.get("/users")
async def list_users_admin(_=Depends(require_admin)):
    from xoai.users import service as users_service
    return await users_service.list_users()


class QuotaUpdate(BaseModel):
    limit_bytes: int


class ConsolidationRequest(BaseModel):
    action: str
    target_lesson_id: Optional[str] = None


def _serialize_document(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_document(item) for item in value]
    if isinstance(value, dict):
        data = {}
        for key, item in value.items():
            normalized_key = "id" if key == "_id" else key
            data[normalized_key] = _serialize_document(item)
        return data
    return value


@router.put("/users/{user_id}/quota")
async def update_user_quota(user_id: str, req: QuotaUpdate, _=Depends(require_admin)):
    from bson import ObjectId
    db = get_db()
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"quota_limit_bytes": req.limit_bytes}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "User not found")
    return {"message": "Quota updated"}


@router.get("/stats")
async def dashboard_stats(_=Depends(require_admin)):
    db = get_db()
    total_users = await db.users.count_documents({})
    pending_users = await db.users.count_documents({"status": "pending"})
    total_conversations = await db.conversations.count_documents({})
    open_tickets = await db.tickets.count_documents({"status": "open"})

    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "total_conversations": total_conversations,
        "open_tickets": open_tickets,
    }


@router.get("/query-runs")
async def list_query_runs(limit: int = 50, _=Depends(require_admin)):
    db = get_db()
    runs = await db.query_runs.find({}).sort("created_at", -1).limit(limit).to_list(limit)
    return [_serialize_document(run) for run in runs]


@router.get("/query-runs/{query_id}")
async def get_query_run_detail(query_id: str, _=Depends(require_admin)):
    db = get_db()
    run = await db.query_runs.find_one({"query_id": query_id})
    if not run:
        raise HTTPException(404, "Query run not found")
    return _serialize_document(run)


@router.get("/experience/insights")
async def list_experience_insights(limit: int = 50, _=Depends(require_admin)):
    db = get_db()
    docs = await db.experience_insights.find({}).sort("updated_at", -1).limit(limit).to_list(limit)
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
    return docs


@router.get("/experience/lessons")
async def list_experience_lessons(limit: int = 50, _=Depends(require_admin)):
    db = get_db()
    docs = await db.experience_lessons.find({}).sort("created_at", -1).limit(limit).to_list(limit)
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
    return docs


@router.get("/experience/consolidations")
async def get_experience_consolidations(limit: int = 100, _=Depends(require_admin)):
    return await list_consolidations(limit)


@router.post("/experience/lessons/{lesson_id}/consolidate")
async def consolidate_experience_lesson(lesson_id: str, req: ConsolidationRequest, _=Depends(require_admin)):
    try:
        return await apply_consolidation_action(
            lesson_id=lesson_id,
            action=req.action,
            target_lesson_id=req.target_lesson_id,
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/prompt-candidates")
async def list_prompt_candidates(limit: int = 50, _=Depends(require_admin)):
    db = get_db()
    docs = await db.prompt_variants.find({}).sort("created_at", -1).limit(limit).to_list(limit)
    return [_serialize_document(doc) for doc in docs]


@router.post("/prompt-candidates/{candidate_id}/evaluate")
async def evaluate_candidate(candidate_id: str, _=Depends(require_admin)):
    try:
        return await evaluate_prompt_candidate(candidate_id)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/prompt-candidates/{candidate_id}/promote")
async def promote_candidate(candidate_id: str, _=Depends(require_admin)):
    try:
        return await set_prompt_candidate_status(candidate_id, "promoted")
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/prompt-candidates/{candidate_id}/reject")
async def reject_candidate(candidate_id: str, _=Depends(require_admin)):
    try:
        return await set_prompt_candidate_status(candidate_id, "rejected")
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/prompt-candidates/{candidate_id}/benchmark")
async def benchmark_candidate(candidate_id: str, _=Depends(require_admin)):
    try:
        return _serialize_document(await run_prompt_candidate_benchmark(candidate_id))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/prompt-candidates/{candidate_id}/benchmarks")
async def list_candidate_benchmarks(candidate_id: str, _=Depends(require_admin)):
    try:
        return _serialize_document(await get_candidate_benchmarks(candidate_id))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/prompt-versions")
async def prompt_versions(limit: int = 100, _=Depends(require_admin)):
    try:
        return _serialize_document(await list_prompt_versions(limit))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/prompt-versions/{version_id}")
async def prompt_version_detail(version_id: str, _=Depends(require_admin)):
    try:
        return _serialize_document(await get_prompt_version_detail(version_id))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/prompt-versions/{version_id}/rollback")
async def rollback_version(version_id: str, _=Depends(require_admin)):
    try:
        return _serialize_document(await rollback_prompt_version(version_id))
    except Exception as e:
        raise HTTPException(400, str(e))
