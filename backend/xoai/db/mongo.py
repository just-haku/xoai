import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from xoai.config import settings

logger = logging.getLogger("xoai.db.mongo")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_mongo():
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongo_uri)
    _db = _client.get_default_database()

    # Create indexes
    await _db.users.create_index("email", unique=True, sparse=True)
    await _db.users.create_index("username", unique=True, sparse=True)
    await _db.conversations.create_index("user_id")
    await _db.conversations.create_index("chat_id", unique=True)
    await _db.messages.create_index("conversation_id")
    await _db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
    await _db.api_keys.create_index("user_id")
    await _db.tickets.create_index("user_id")
    await _db.settings.create_index("key", unique=True)
    await _db.refresh_sessions.create_index("session_id", unique=True)
    await _db.refresh_sessions.create_index([("user_id", 1), ("revoked_at", 1)])
    await _db.refresh_sessions.create_index("expires_at", expireAfterSeconds=0)
    await _db.proxy_handoffs.create_index("token_hash", unique=True)
    await _db.proxy_handoffs.create_index("expires_at", expireAfterSeconds=0)
    await _db.verification_codes.create_index([("user_id", 1), ("type", 1)], unique=True)
    await _db.verification_codes.create_index("expires_at", expireAfterSeconds=0)
    await _db.password_reset_tokens.create_index("token_hash", unique=True)
    await _db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await _db.jobs.create_index([("status", 1), ("run_after", 1)])
    await _db.file_operations.create_index([("user_id", 1), ("path", 1)], unique=True)
    await _db.file_operations.create_index("status")
    await _db.agent_profiles.create_index("agent_key", unique=True)
    await _db.agent_profiles.create_index([("role", 1), ("enabled", 1)])
    await _db.upload_sessions.create_index("upload_id", unique=True)
    await _db.upload_sessions.create_index("expires_at", expireAfterSeconds=0)
    await _db.storage_artifacts.create_index([("retention_class", 1), ("expires_at", 1)])
    await _db.storage_artifacts.create_index([("user_id", 1), ("path", 1)], unique=True)
    await _db.scheduled_tasks.create_index([("enabled", 1), ("next_run_at", 1)])
    await _db.task_runs.create_index([("scheduled_task_id", 1), ("created_at", -1)])
    await _db.memory_engrams.create_index([("user_id", 1), ("created_at", -1)])
    await _db.query_runs.create_index("query_id", unique=True)
    await _db.query_runs.create_index([("conversation_id", 1), ("created_at", -1)])
    await _db.experience_lessons.create_index([("profile_key", 1), ("utility_score", -1)])
    await _db.experience_lessons.create_index([("profile_key", 1), ("normalized_statement", 1), ("keep_state", 1)])
    await _db.experience_insights.create_index("profile_key", unique=True)
    await _db.experience_profiles.create_index("profile_key", unique=True)
    await _db.experience_consolidations.create_index([("profile_key", 1), ("created_at", -1)])
    await _db.prompt_variants.create_index([("role", 1), ("promotion_status", 1)])
    await _db.prompt_evaluations.create_index([("candidate_id", 1), ("created_at", -1)])
    await _db.prompt_promotions.create_index([("role", 1), ("created_at", -1)])
    await _db.prompt_bench_runs.create_index([("candidate_id", 1), ("created_at", -1)])
    await _db.prompt_versions.create_index([("role", 1), ("version", -1)], unique=True)
    await _db.prompt_versions.create_index([("role", 1), ("status", 1)])
    await _db.mcp_servers.create_index([("name", 1), ("user_id", 1)], unique=True)
    await _db.consensus_proposals.create_index("proposal_id", unique=True)
    await _db.consensus_proposals.create_index([("user_id", 1), ("created_at", -1)])

    logger.info("✅ MongoDB connected.")


async def close_mongo():
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB disconnected.")


class DatabaseProxy:
    def __getattr__(self, name):
        if _db is None:
            raise RuntimeError("MongoDB not connected. Call connect_mongo() first.")
        return getattr(_db, name)

db = DatabaseProxy()

def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB not connected. Call connect_mongo() first.")
    return _db
