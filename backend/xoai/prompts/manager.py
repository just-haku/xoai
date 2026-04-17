import os
import logging
from functools import lru_cache

logger = logging.getLogger("xoai.prompts.manager")

PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))

@lru_cache(maxsize=20)
def _load_raw_prompt(name: str) -> str:
    """Loads the raw content of a prompt file."""
    path = os.path.join(PROMPTS_DIR, f"{name}.md")
    if not os.path.exists(path):
        logger.warning(f"Prompt file not found: {path}. Using default empty string.")
        return ""
    
    with open(path, "r") as f:
        return f.read().strip()


def get_prompt_source(name: str) -> str:
    """Return the current on-disk prompt source."""
    return _load_raw_prompt(name)

def get_prompt(name: str, **kwargs) -> str:
    """Gets a prompt by name and templates it with kwargs."""
    raw = _load_raw_prompt(name)
    if not raw:
        return ""
    
    try:
        if kwargs:
            return raw.format(**kwargs)
        return raw
    except KeyError as e:
        logger.error(f"Missing template variable {e} for prompt {name}")
        return raw
    except Exception as e:
        logger.error(f"Error templating prompt {name}: {e}")
        return raw

def reload_prompts():
    """Clears the LRU cache to reload prompts from disk."""
    _load_raw_prompt.cache_clear()


async def get_active_prompt_version(role: str) -> dict | None:
    from xoai.db.mongo import get_db

    db = get_db()
    return await db.prompt_versions.find_one({"role": role, "status": "active"}, sort=[("version", -1)])


async def get_runtime_prompt(name: str, role: str | None = None, **kwargs) -> str:
    active = await get_active_prompt_version(role or name)
    raw = (active or {}).get("content") or _load_raw_prompt(name)
    if not raw:
        return ""

    try:
        if kwargs:
            return raw.format(**kwargs)
        return raw
    except KeyError as e:
        logger.error(f"Missing template variable {e} for prompt {name}")
        return raw
    except Exception as e:
        logger.error(f"Error templating prompt {name}: {e}")
        return raw
