import logging
import redis.asyncio as aioredis

from xoai.config import settings

logger = logging.getLogger("xoai.db.redis")

_redis: aioredis.Redis | None = None


async def connect_redis():
    global _redis
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    await _redis.ping()
    logger.info("✅ Redis connected.")


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        logger.info("Redis disconnected.")


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not connected. Call connect_redis() first.")
    return _redis
