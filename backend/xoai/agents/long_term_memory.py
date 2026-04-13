"""Long Term Memory — Redis-backed key-value store for 'facts' or 'hallucination checks'."""

import json
import logging
from xoai.db.redis import get_redis

logger = logging.getLogger("xoai.agents.ltm")


async def store_fact(user_id: str, key: str, value: str):
    """Store a fact in Redis for quick retrieval."""
    redis = get_redis()
    redis_key = f"ltm:{user_id}:{key}"
    await redis.set(redis_key, value)
    logger.info(f"Fact stored for user {user_id}: {key}")


async def get_fact(user_id: str, key: str) -> str | None:
    """Retrieve a fact from Redis."""
    redis = get_redis()
    redis_key = f"ltm:{user_id}:{key}"
    return await redis.get(redis_key)


async def search_facts(user_id: str, query: str) -> list[str]:
    """
    Search for related facts in user's LTM.
    In a simple implementation, we might just scan keys or use a dedicated search index.
    For Phase 4, we'll keep it as a simple retrieval of known important keys.
    """
    # TODO: Implement keyword or vector search if required.
    # For now, we'll just return a manual list of 'profile' or 'config' facts.
    facts = []
    for k in ["profile", "persona", "preferences"]:
        val = await get_fact(user_id, k)
        if val:
            facts.append(f"{k}: {val}")
    return facts
