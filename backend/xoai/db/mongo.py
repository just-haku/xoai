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
    await _db.users.create_index("email", unique=True)
    await _db.conversations.create_index("user_id")
    await _db.messages.create_index("conversation_id")
    await _db.api_keys.create_index("user_id")
    await _db.tickets.create_index("user_id")
    await _db.settings.create_index("key", unique=True)

    logger.info("✅ MongoDB connected.")


async def close_mongo():
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB disconnected.")


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB not connected. Call connect_mongo() first.")
    return _db
