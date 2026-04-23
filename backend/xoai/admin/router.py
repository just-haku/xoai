"""Admin dashboard routes: settings CRUD, stats."""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any

from bson import ObjectId
from xoai.auth.dependencies import require_admin
from xoai.auth.service import create_proxy_handoff
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
from xoai.prompts.service import (
    activate_prompt_version,
    create_prompt_version,
    list_prompt_families,
    prompt_diff,
)
from xoai.storage_gc import run_storage_gc

router = APIRouter()
logger = logging.getLogger("xoai.admin")


class SettingUpdate(BaseModel):
    key: str
    value: dict


class PromptVersionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)
    mutation_reason: str = Field(min_length=3, max_length=200)


class AgentProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_key: str = Field(min_length=2, max_length=64)
    role: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=120)
    prompt_name: str = Field(min_length=2, max_length=64)
    provider: str = Field(min_length=2, max_length=32)
    model: str = Field(min_length=1, max_length=200)
    key: str | None = None
    base_url: str | None = None
    tool_allowlist: list[str] = Field(default_factory=list)
    risk_policy: dict = Field(default_factory=dict)
    enabled: bool = True
    max_concurrency: int = Field(default=1, ge=1, le=64)


class GcRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: bool = False


def _serialize_user_summary(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "username": user.get("username", ""),
        "name": user.get("name", ""),
        "role": user.get("role", "user"),
        "status": user.get("status", "pending"),
    }


@router.get("/settings")
async def list_settings(_=Depends(require_admin)):
    """List all setting keys (values are encrypted, returned on individual get)."""
    return await service.list_setting_keys()


@router.get("/settings/smtp")
async def get_smtp_setting(_=Depends(require_admin)):
    val = await service.get_setting("smtp")
    return {"key": "smtp", "value": val}


@router.get("/settings/agent_0_bridge_mode")
async def get_bridge_mode_setting(_=Depends(require_admin)):
    val = await service.get_setting("agent_0_bridge_mode")
    return {"key": "agent_0_bridge_mode", "value": val}


@router.get("/settings/admin_workspace_path")
async def get_admin_workspace_path_setting(_=Depends(require_admin)):
    val = await service.get_setting("admin_workspace_path")
    return {"key": "admin_workspace_path", "value": val}


@router.get("/settings/{key}")
async def get_setting(key: str, _=Depends(require_admin)):
    """Get a setting by key. Returns null value if not found instead of 404 to avoid frontend crashes."""
    # Ensure common settings don't 404
    val = await service.get_setting(key)
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


@router.post("/users/{user_id}/proxy-session")
async def create_user_proxy_session(user_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    try:
        object_id = ObjectId(user_id)
    except Exception as exc:
        raise HTTPException(404, "User not found") from exc

    target_user = await db.users.find_one({"_id": object_id})
    if not target_user:
        raise HTTPException(404, "User not found")
    if target_user.get("status") != "approved":
        raise HTTPException(409, "User is not available for proxy sessions")

    handoff = await create_proxy_handoff(str(target_user["_id"]), target_user.get("role", "user"), admin["id"])
    logger.info(
        "Created proxy session handoff",
        extra={
            "admin_id": admin["id"],
            "target_user_id": str(target_user["_id"]),
            "session_id": handoff["session_id"],
        },
    )
    return {
        "handoff_token": handoff["handoff_token"],
        "expires_at": handoff["expires_at"].isoformat(),
        "session_id": handoff["session_id"],
        "user": _serialize_user_summary(target_user),
    }


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


@router.get("/prompts")
async def list_prompt_registry(_=Depends(require_admin)):
    return _serialize_document(await list_prompt_families())


@router.post("/prompts/{role}/versions")
async def create_prompt_registry_version(role: str, req: PromptVersionCreateRequest, admin: dict = Depends(require_admin)):
    return _serialize_document(await create_prompt_version(role, req.content, req.mutation_reason, admin["id"]))


@router.post("/prompts/versions/{version_id}/activate")
async def activate_prompt_registry_version(version_id: str, _=Depends(require_admin)):
    return _serialize_document(await activate_prompt_version(version_id))


@router.get("/prompts/versions/{version_id}/diff")
async def get_prompt_registry_diff(version_id: str, _=Depends(require_admin)):
    return _serialize_document(await prompt_diff(version_id))


@router.get("/agent-profiles")
async def list_agent_profiles(_=Depends(require_admin)):
    db = get_db()
    docs = await db.agent_profiles.find({}).sort([("role", 1), ("agent_key", 1)]).to_list(200)
    return [_serialize_document(doc) for doc in docs]


@router.post("/agent-profiles")
async def create_agent_profile(req: AgentProfileRequest, _=Depends(require_admin)):
    db = get_db()
    doc = req.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    await db.agent_profiles.update_one({"agent_key": req.agent_key}, {"$set": doc}, upsert=True)
    stored = await db.agent_profiles.find_one({"agent_key": req.agent_key})
    return _serialize_document(stored)


@router.put("/agent-profiles/{agent_key}")
async def update_agent_profile(agent_key: str, req: AgentProfileRequest, _=Depends(require_admin)):
    db = get_db()
    payload = req.model_dump()
    payload["agent_key"] = agent_key
    payload["updated_at"] = datetime.utcnow()
    await db.agent_profiles.update_one({"agent_key": agent_key}, {"$set": payload}, upsert=True)
    stored = await db.agent_profiles.find_one({"agent_key": agent_key})
    return _serialize_document(stored)


@router.delete("/agent-profiles/{agent_key}")
async def delete_agent_profile(agent_key: str, _=Depends(require_admin)):
    db = get_db()
    await db.agent_profiles.delete_one({"agent_key": agent_key})
    return {"status": "deleted", "agent_key": agent_key}


@router.post("/storage-gc/run")
async def trigger_storage_gc(req: GcRunRequest, _=Depends(require_admin)):
    return _serialize_document(await run_storage_gc(dry_run=req.dry_run))


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


# --- Scheduler CRUD ---

class ScheduledTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    cron: str = Field(min_length=5, max_length=64)
    timezone: str = Field(default="UTC", max_length=64)
    enabled: bool = True
    agent_key: str = Field(min_length=2, max_length=64)
    workspace_scope: Optional[str] = None
    tool_policy: dict = Field(default_factory=dict)
    payload: dict = Field(default_factory=dict)


class ScheduledTaskToggle(BaseModel):
    enabled: bool


@router.get("/scheduled-tasks")
async def list_scheduled_tasks(limit: int = 100, _=Depends(require_admin)):
    from xoai.scheduler import list_scheduled_tasks as _list
    return [_serialize_document(t) for t in await _list(limit)]


@router.get("/scheduled-tasks/{task_id}")
async def get_scheduled_task(task_id: str, _=Depends(require_admin)):
    from xoai.scheduler import get_scheduled_task as _get
    try:
        return _serialize_document(await _get(task_id))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/scheduled-tasks")
async def create_scheduled_task(req: ScheduledTaskRequest, admin: dict = Depends(require_admin)):
    from xoai.scheduler import create_scheduled_task as _create
    doc = await _create(req.model_dump(), admin["id"])
    return _serialize_document(doc)


@router.put("/scheduled-tasks/{task_id}")
async def update_scheduled_task(task_id: str, req: ScheduledTaskRequest, _=Depends(require_admin)):
    from xoai.scheduler import update_scheduled_task as _update
    return _serialize_document(await _update(task_id, req.model_dump()))


@router.patch("/scheduled-tasks/{task_id}/toggle")
async def toggle_scheduled_task(task_id: str, req: ScheduledTaskToggle, _=Depends(require_admin)):
    from xoai.scheduler import toggle_scheduled_task as _toggle
    return _serialize_document(await _toggle(task_id, req.enabled))


@router.delete("/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: str, _=Depends(require_admin)):
    from xoai.scheduler import delete_scheduled_task as _delete
    await _delete(task_id)
    return {"status": "deleted"}


@router.get("/scheduled-tasks/{task_id}/runs")
async def list_task_runs(task_id: str, limit: int = 50, _=Depends(require_admin)):
    from xoai.scheduler import list_task_runs as _runs
    return [_serialize_document(r) for r in await _runs(task_id, limit)]


# --- Engram Compaction ---

class EngramCompactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stale_days: int = Field(default=7, ge=1, le=365)
    batch_size: int = Field(default=50, ge=1, le=500)


@router.post("/engram-compaction/run")
async def trigger_engram_compaction(req: EngramCompactionRequest, _=Depends(require_admin)):
    from xoai.agents.memory import compact_engrams
    return _serialize_document(await compact_engrams(stale_days=req.stale_days, batch_size=req.batch_size))

