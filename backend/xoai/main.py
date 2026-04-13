import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from xoai.db.mongo import connect_mongo, close_mongo
from xoai.db.redis import connect_redis, close_redis

logger = logging.getLogger("xoai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("🥭 XOAI starting up...")
    await connect_mongo()
    await connect_redis()
    
    # Start bridges as background tasks
    from xoai.channels.zalo_bridge import start_zalo_bridge
    from xoai.channels.discord_bridge import start_discord_bridge
    from xoai.channels.telegram_bridge import start_telegram_bridge
    
    app.state.zalo_task = asyncio.create_task(start_zalo_bridge())
    app.state.discord_task = asyncio.create_task(start_discord_bridge())
    app.state.telegram_task = asyncio.create_task(start_telegram_bridge())
    
    logger.info("✅ XOAI ready + Bridges starting.")
    yield
    logger.info("🛑 XOAI shutting down...")
    
    # Cancel bridges
    for task_name in ["zalo_task", "discord_task", "telegram_task"]:
        task = getattr(app.state, task_name, None)
        if task:
            task.cancel()
    
    await close_redis()
    await close_mongo()


def create_app() -> FastAPI:
    app = FastAPI(
        title="XOAI",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health check ---
    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.post("/api/models/fetch")
    async def fetch_models(data: dict):
        provider = data.get("provider")
        api_key = data.get("api_key")
        
        # Real logic would use httpx to hit Google/OpenAI
        models = []
        if provider == "gemini":
            models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]
        elif provider == "openai":
            models = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        
        # Save to DB cache
        from xoai.db.mongo import db
        await db.settings.update_one(
            {"type": "models_cache", "provider": provider},
            {"$set": {"models": models, "updated_at": datetime.now(timezone.utc)}},
            upsert=True
        )
        return {"status": "success", "models": models}

    # --- Register routers ---
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
