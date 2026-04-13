"""LLM Pool Manager — Multi-provider key selection with 429 fallback."""

import logging
from datetime import datetime, timezone, timedelta

from xoai.db.mongo import get_db
from xoai.auth.service import decrypt_value
from xoai.admin.service import get_setting
from xoai.agents.providers import GeminiProvider, OpenAIProvider, LLMProvider

logger = logging.getLogger("xoai.agents.llm_pool")


async def get_agent_config(agent_name: str) -> dict | None:
    """Get model+key config for a named agent (agent_0, agent_1, agent_2) from admin settings."""
    return await get_setting(f"{agent_name}_config")


async def get_user_agent_key(user_id: str) -> dict | None:
    """Get the user's personal API key from the api_keys collection."""
    db = get_db()
    doc = await db.api_keys.find_one(
        {"user_id": user_id, "is_fallback": False},
        sort=[("created_at", -1)],
    )
    if not doc:
        return None
    return {
        "provider": doc["provider"],
        "key": decrypt_value(doc["key_encrypted"]),
        "model": doc.get("model"),
    }


async def get_fallback_key(provider: str = None) -> dict | None:
    """Get a server fallback pool key. Optionally filtered by provider."""
    db = get_db()
    query = {"is_fallback": True, "user_id": None}
    if provider:
        query["provider"] = provider

    # Skip keys that are rate-limited
    query["$or"] = [
        {"rate_limit_reset_at": None},
        {"rate_limit_reset_at": {"$lt": datetime.now(timezone.utc)}},
    ]

    doc = await db.api_keys.find_one(query)
    if not doc:
        return None
    return {
        "provider": doc["provider"],
        "key": decrypt_value(doc["key_encrypted"]),
    }


async def mark_rate_limited(user_id: str, reset_seconds: int = 60):
    """Mark a user's key as rate-limited."""
    db = get_db()
    reset_at = datetime.now(timezone.utc) + timedelta(seconds=reset_seconds)
    await db.api_keys.update_one(
        {"user_id": user_id, "is_fallback": False},
        {"$set": {"rate_limit_reset_at": reset_at}},
    )


async def get_provider(config: dict) -> LLMProvider:
    """Instantiate a provider based on config."""
    provider_name = config.get("provider", "gemini").lower()
    api_key = config.get("key")
    
    if provider_name == "gemini":
        return GeminiProvider(api_key=api_key)
    elif provider_name == "openai":
        return OpenAIProvider(api_key=api_key, base_url=config.get("base_url"))
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")


async def list_available_models() -> list[dict]:
    """Ping configured providers and return available models."""
    models = []

    # Check admin-configured agents
    for agent_name in ["agent_0", "agent_1", "agent_2"]:
        config = await get_agent_config(agent_name)
        if config and config.get("model"):
            models.append({
                "id": config["model"],
                "provider": config.get("provider", "unknown"),
                "source": agent_name,
            })

    # Check fallback pool
    db = get_db()
    async for doc in db.api_keys.find({"is_fallback": True}):
        models.append({
            "provider": doc["provider"],
            "source": "fallback_pool",
        })

    return models
