import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from xoai.auth.dependencies import require_admin
from xoai.agents.memory import migrate_embedded_conversation_messages
from xoai.config import settings, validate_runtime_settings
from xoai.scheduler.worker import start_scheduler, stop_scheduler
from xoai.db.mongo import close_mongo, connect_mongo, get_db
from xoai.db.redis import close_redis, connect_redis, get_redis
from xoai.job_handlers import register_job_handlers
from xoai.jobs import job_manager
from xoai.metrics import metrics
from xoai.prompts.service import seed_prompt_versions_from_disk
from xoai.workspace.service import recover_in_progress_file_operations

logger = logging.getLogger("xoai")


async def _job_poller() -> None:
    while True:
        await job_manager.process_pending()
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("XOAI starting up")
    validate_runtime_settings()
    await connect_mongo()
    await connect_redis()
    register_job_handlers()
    seeded_prompts = await seed_prompt_versions_from_disk()
    await job_manager.enqueue("restore_tenant_bots", {"startup_jitter_seconds": settings.restart_jitter_seconds}, jitter_seconds=settings.restart_jitter_seconds)
    await job_manager.enqueue("storage_gc", {"startup_jitter_seconds": settings.restart_jitter_seconds}, jitter_seconds=settings.restart_jitter_seconds)
    migrated = await migrate_embedded_conversation_messages()
    recovered = await recover_in_progress_file_operations()
    if seeded_prompts:
        logger.info("Seeded prompt versions from disk", extra={"count": seeded_prompts})
    if migrated:
        logger.info("Migrated embedded conversation messages", extra={"count": migrated})
    if recovered:
        logger.info("Recovered interrupted file operations", extra={"count": recovered})
    app.state.job_poller = asyncio.create_task(_job_poller())
    job_manager.track_task(app.state.job_poller)
    await start_scheduler()
    logger.info("XOAI ready — Chronos scheduler active")
    yield
    logger.info("XOAI shutting down")
    await stop_scheduler()
    await job_manager.drain()
    from xoai.mcp.client import mcp_manager

    await mcp_manager.disconnect_all()
    await close_redis()
    await close_mongo()


def create_app() -> FastAPI:
    app = FastAPI(
        title="XOAI",
        version="1.0.0",
        lifespan=lifespan,
    )

    if settings.enable_cors and settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "1.0.0", "metrics": metrics.snapshot()}

    @app.get("/api/ready")
    async def ready():
        validate_runtime_settings()
        db = get_db()
        redis = get_redis()
        await db.command("ping")
        await redis.ping()
        return {"status": "ready"}

    @app.post("/api/models/fetch")
    async def fetch_models(data: dict, _=Depends(require_admin)):
        provider = data.get("provider")

        models = []
        if provider == "gemini":
            models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]
        elif provider == "openai":
            models = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

        db = get_db()
        cache_key = f"models_cache:{provider}"
        await db.settings.update_one(
            {"key": cache_key},
            {
                "$set": {
                    "key": cache_key,
                    "type": "models_cache",
                    "provider": provider,
                    "models": models,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
        return {"status": "success", "models": models}

    from xoai.auth.router import router as auth_router
    from xoai.users.router import router as users_router
    from xoai.chats.router import router as chats_router
    from xoai.admin.router import router as admin_router
    from xoai.workspace.router import router as workspace_router
    from xoai.mcp.router import router as mcp_router
    from xoai.tickets.router import router as tickets_router
    from xoai.channels.websocket import router as ws_router

    app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
    app.include_router(users_router, prefix="/api/users", tags=["Users"])
    app.include_router(chats_router, prefix="/api/chats", tags=["Chats"])
    app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
    app.include_router(workspace_router, prefix="/api/workspace", tags=["Workspace"])
    app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP"])
    app.include_router(tickets_router, prefix="/api/tickets", tags=["Tickets"])
    app.include_router(ws_router, tags=["WebSocket"])

    return app
