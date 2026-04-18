"""Conversation memory, Qdrant-backed vector retrieval, and engram compaction.

Provides:
  - Message persistence and retrieval from MongoDB
  - Async embedding pipeline (Gemini text-embedding-004) to chunk and embed messages into Qdrant
  - LLM-powered engram compaction for long-term memory summarization
  - Semantic retrieval for context injection
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger("xoai.agents.memory")

# ---------------------------------------------------------------------------
# Qdrant constants — aligned to Gemini text-embedding-004 output (768-d)
# ---------------------------------------------------------------------------
QDRANT_COLLECTION = "xoai_messages"
EMBEDDING_DIMENSION = 768
ENGRAM_COLLECTION = "xoai_engrams"
MAX_CHUNK_CHARS = 1200
OVERLAP_CHARS = 200

# Gemini Embedding API
_GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
_EMBED_MAX_RETRIES = 3
_EMBED_RETRY_BASE_DELAY = 1.5  # seconds, exponential backoff


# ---------------------------------------------------------------------------
# Embedding Engine (Gemini text-embedding-004 REST API)
# ---------------------------------------------------------------------------

def _get_gemini_api_key() -> str | None:
    """Retrieve the Gemini API key from the environment via settings or agent_0 config."""
    import os
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    # Fallback: try to pull from admin-configured agent_0
    # (sync fallback for startup; async callers should pre-resolve)
    return None


async def _get_gemini_api_key_async() -> str | None:
    """Async resolve: check env first, then pull from agent_0 admin config."""
    import os
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        from xoai.admin.service import get_setting
        config = await get_setting("agent_0_config")
        if config and config.get("key"):
            return config["key"]
    except Exception:
        pass
    return None


async def embed_text(text: str) -> list[float] | None:
    """Generate a 768-dimensional embedding via Gemini text-embedding-004.

    Includes exponential backoff for 429 rate-limit responses and
    graceful fallback to None on persistent failure.
    """
    api_key = await _get_gemini_api_key_async()
    if not api_key:
        logger.warning("No Gemini API key available for embeddings; skipping")
        return None

    payload = {
        "content": {"parts": [{"text": text[:8000]}]},  # API limit ~10k chars
    }
    params = {"key": api_key}

    for attempt in range(_EMBED_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(_GEMINI_EMBED_URL, json=payload, params=params)

                if resp.status_code == 429:
                    delay = _EMBED_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "Embedding API rate-limited (429), retry %d/%d in %.1fs",
                        attempt + 1, _EMBED_MAX_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                resp.raise_for_status()
                data = resp.json()
                values = data.get("embedding", {}).get("values", [])
                if values and len(values) == EMBEDDING_DIMENSION:
                    return values
                logger.warning(
                    "Unexpected embedding dimension: got %d, expected %d",
                    len(values), EMBEDDING_DIMENSION,
                )
                return values if values else None

        except httpx.HTTPStatusError as exc:
            logger.error("Embedding API HTTP error (%d): %s", exc.response.status_code, exc.response.text[:300])
            return None
        except Exception as exc:
            logger.error("Embedding request failed (attempt %d): %s", attempt + 1, exc)
            if attempt == _EMBED_MAX_RETRIES - 1:
                return None
            await asyncio.sleep(_EMBED_RETRY_BASE_DELAY * (2 ** attempt))

    return None


def _deterministic_fallback_embedding(text: str) -> list[float]:
    """Hash-based pseudo-embedding fallback when the API is unavailable.

    Only used as a last-resort so vector operations don't crash entirely.
    """
    text_bytes = text.encode("utf-8")
    vectors = []
    for i in range(EMBEDDING_DIMENSION):
        h = hashlib.sha256(text_bytes + i.to_bytes(2, "big")).digest()
        val = int.from_bytes(h[:4], "big") / (2**32) * 2 - 1
        vectors.append(val)
    magnitude = sum(v * v for v in vectors) ** 0.5
    if magnitude > 0:
        vectors = [v / magnitude for v in vectors]
    return vectors


async def get_embedding(text: str) -> list[float]:
    """Primary embedding function: tries Gemini API, falls back to deterministic hash."""
    embedding = await embed_text(text)
    if embedding is not None:
        return embedding
    logger.debug("Using deterministic fallback embedding")
    return _deterministic_fallback_embedding(text)


# ---------------------------------------------------------------------------
# Core message persistence (MongoDB)
# ---------------------------------------------------------------------------


async def get_conversation_messages(conversation_id: str, limit: int = 50) -> list:
    """Fetch recent messages for a conversation."""
    from xoai.db.mongo import get_db
    db = get_db()
    cursor = db.messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    docs.reverse()
    messages = []
    for doc in docs:
        msg = {
            "role": doc["role"],
            "content": doc.get("content", ""),
        }
        if doc.get("tool_calls"):
            msg["tool_calls"] = doc["tool_calls"]
        messages.append(msg)
    return messages


async def save_message(conversation_id: str, role: str, content: str, **kwargs):
    """Save a message to the conversation and dispatch async embedding."""
    from xoai.db.mongo import get_db
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "tool_calls": kwargs.get("tool_calls", []),
        "channel_metadata": kwargs.get("channel_metadata", {}),
        "created_at": now,
    }
    result = await db.messages.insert_one(doc)

    user_id = kwargs.get("user_id")
    if user_id:
        await db.conversations.update_one(
            {"chat_id": conversation_id, "user_id": user_id},
            {
                "$setOnInsert": {
                    "chat_id": conversation_id,
                    "user_id": user_id,
                    "title": None,
                    "summary_compressed": None,
                    "message_count": 0,
                    "created_at": now,
                },
                "$set": {"updated_at": now},
                "$inc": {"message_count": 1},
            },
            upsert=True,
        )

        # Fire-and-forget async embedding into Qdrant
        asyncio.create_task(
            _embed_message_to_qdrant(
                message_id=str(result.inserted_id),
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
            )
        )


async def compress_if_needed(conversation_id: str, model_context_window: int = 128000):
    """Check if compression is needed and compress old messages."""
    # TODO: Phase 4 — Use configurable compression agent from admin settings
    pass


async def migrate_embedded_conversation_messages(limit: int = 100) -> int:
    """Backfill embedded conversation messages into the canonical messages collection."""
    from xoai.db.mongo import get_db

    db = get_db()
    conversations = await db.conversations.find(
        {
            "messages": {"$exists": True, "$ne": []},
            "embedded_messages_migrated_at": {"$exists": False},
        }
    ).limit(limit).to_list(limit)

    migrated = 0
    for convo in conversations:
        chat_id = convo["chat_id"]
        existing = await db.messages.count_documents({"conversation_id": chat_id})
        if existing == 0:
            docs = []
            for message in convo.get("messages", []):
                docs.append(
                    {
                        "conversation_id": chat_id,
                        "role": message.get("role", "assistant"),
                        "content": message.get("content", ""),
                        "tool_calls": message.get("tool_calls", []),
                        "channel_metadata": message.get("metadata", {}),
                        "created_at": message.get("created_at"),
                    }
                )
            if docs:
                await db.messages.insert_many(docs)
        await db.conversations.update_one(
            {"_id": convo["_id"]},
            {
                "$set": {
                    "embedded_messages_migrated_at": datetime.now(timezone.utc),
                    "message_count": await db.messages.count_documents({"conversation_id": chat_id}),
                },
                "$unset": {"messages": ""},
            },
        )
        migrated += 1
    return migrated


# ---------------------------------------------------------------------------
# Qdrant Vector Memory Pipeline
# ---------------------------------------------------------------------------


def _get_qdrant_client():
    """Lazy-initialize and return the Qdrant async client."""
    try:
        from qdrant_client import QdrantClient
        from xoai.config import settings
        return QdrantClient(url=settings.qdrant_url, timeout=10)
    except ImportError:
        logger.warning("qdrant-client not installed; vector memory disabled")
        return None
    except Exception as exc:
        logger.warning("Qdrant connection failed: %s", exc)
        return None


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


async def _ensure_qdrant_collection(client) -> bool:
    """Ensure the Qdrant collection exists."""
    try:
        from qdrant_client.models import Distance, VectorParams
        collections = client.get_collections().collections
        names = {c.name for c in collections}
        if QDRANT_COLLECTION not in names:
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", QDRANT_COLLECTION)
        if ENGRAM_COLLECTION not in names:
            client.create_collection(
                collection_name=ENGRAM_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", ENGRAM_COLLECTION)
        return True
    except Exception as exc:
        logger.warning("Failed to ensure Qdrant collections: %s", exc)
        return False


async def _embed_message_to_qdrant(
    *,
    message_id: str,
    conversation_id: str,
    user_id: str,
    role: str,
    content: str,
) -> None:
    """Chunk and embed a message into Qdrant after it is committed to Mongo."""
    if not content or not content.strip():
        return

    client = _get_qdrant_client()
    if not client:
        return

    if not await _ensure_qdrant_collection(client):
        return

    try:
        from qdrant_client.models import PointStruct

        chunks = _chunk_text(content)
        points = []
        for i, chunk in enumerate(chunks):
            embedding = await get_embedding(chunk)
            point_id = uuid.uuid4().hex
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "message_id": message_id,
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "role": role,
                        "chunk_index": i,
                        "chunk_text": chunk[:2000],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )

        if points:
            client.upsert(collection_name=QDRANT_COLLECTION, points=points)

    except Exception as exc:
        logger.warning("Qdrant embedding failed for message %s: %s", message_id, exc)


async def semantic_search(
    query: str,
    user_id: str,
    limit: int = 5,
    score_threshold: float = 0.3,
) -> list[dict]:
    """Search Qdrant for semantically similar message chunks."""
    client = _get_qdrant_client()
    if not client:
        return []

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        embedding = await get_embedding(query)
        results = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=embedding,
            query_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=limit,
            score_threshold=score_threshold,
        )
        return [
            {
                "score": hit.score,
                "chunk_text": hit.payload.get("chunk_text", ""),
                "conversation_id": hit.payload.get("conversation_id", ""),
                "role": hit.payload.get("role", ""),
                "message_id": hit.payload.get("message_id", ""),
            }
            for hit in results
        ]
    except Exception as exc:
        logger.warning("Qdrant semantic search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Engram Compaction — LLM-Powered Synthesis
# ---------------------------------------------------------------------------

ENGRAM_SYSTEM_PROMPT = """You are a memory compaction engine for an AI assistant platform.

Your task: Read the following raw chat thread between a user and an AI assistant.
Produce a dense, structured markdown summary that captures ALL important information.

Output format (use exactly these headers):

## [Core Facts]
- Key factual information, decisions made, technical details, code references
- Include names, dates, versions, URLs, or identifiers mentioned

## [User Preferences]
- Communication style preferences, tool preferences, workflow habits
- Any explicitly stated likes/dislikes or requirements
- Design preferences, technology stack choices

## [Unresolved Tasks]
- Anything the user mentioned needing to do but was not completed
- Open questions or pending decisions
- Items marked as TODO or "later"

Rules:
- Be extremely concise but lose ZERO important information
- Use bullet points exclusively
- Never fabricate information not present in the thread
- If a section has no relevant items, write "None identified"
- Maximum 500 words total"""


async def compact_engrams(
    stale_days: int = 7,
    batch_size: int = 50,
) -> dict:
    """Query Mongo for stale threads, generate dense Memory Engrams
    via LLM synthesis, embed them, and index in Qdrant for semantic retrieval.

    Returns a summary dict with counts.
    """
    from xoai.db.mongo import get_db

    db = get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)

    # Find conversations older than cutoff that haven't been engram-compacted
    stale_conversations = await db.conversations.find(
        {
            "updated_at": {"$lt": cutoff},
            "engram_compacted_at": {"$exists": False},
            "message_count": {"$gt": 3},
        }
    ).limit(batch_size).to_list(batch_size)

    compacted = 0
    engrams_created = 0
    errors = 0

    for convo in stale_conversations:
        chat_id = convo["chat_id"]
        user_id = convo["user_id"]

        # Fetch all messages for this conversation
        messages = await db.messages.find(
            {"conversation_id": chat_id}
        ).sort("created_at", 1).to_list(500)

        if not messages:
            continue

        try:
            engram = await _generate_engram_llm(messages, user_id, chat_id)
        except Exception as exc:
            logger.error("Engram generation failed for %s: %s", chat_id, exc)
            errors += 1
            continue

        if not engram:
            continue

        # Persist to MongoDB
        result = await db.memory_engrams.insert_one(engram)
        engram_id = str(result.inserted_id)

        # Index in Qdrant for semantic retrieval
        await _index_engram_in_qdrant(engram_id, engram)

        # Mark conversation as compacted
        await db.conversations.update_one(
            {"_id": convo["_id"]},
            {"$set": {"engram_compacted_at": datetime.now(timezone.utc)}},
        )

        compacted += 1
        engrams_created += 1

    return {
        "conversations_processed": compacted,
        "engrams_created": engrams_created,
        "errors": errors,
        "stale_cutoff": cutoff.isoformat(),
    }


async def _generate_engram_llm(
    messages: list[dict], user_id: str, conversation_id: str
) -> dict | None:
    """Generate a dense memory engram by dispatching the chat thread to the LLM.

    Uses the internal LLM pool for provider-agnostic generation.
    """
    if not messages:
        return None

    # Build the raw thread text (capped at ~12k chars to stay within context)
    thread_lines = []
    total_chars = 0
    message_ids = []
    for msg in messages:
        content = msg.get("content", "").strip()
        if not content:
            continue
        role = msg.get("role", "unknown")
        line = f"[{role}]: {content}"
        if total_chars + len(line) > 12000:
            break
        thread_lines.append(line)
        total_chars += len(line)
        message_ids.append(str(msg.get("_id", "")))

    if not thread_lines:
        return None

    raw_thread = "\n".join(thread_lines)
    prompt = f"{ENGRAM_SYSTEM_PROMPT}\n\n---\n\n{raw_thread}"

    # Dispatch to the LLM pool
    from xoai.agents.llm_pool import llm_pool
    summary = await llm_pool.generate(prompt)

    if not summary or len(summary.strip()) < 20:
        logger.warning("LLM returned empty/short engram for conversation %s", conversation_id)
        return None

    return {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "summary": summary.strip(),
        "source_message_ids": message_ids[:50],
        "freshness_score": 1.0,
        "confidence_score": 0.9,
        "created_at": datetime.now(timezone.utc),
    }


async def _index_engram_in_qdrant(engram_id: str, engram: dict) -> None:
    """Index an engram in Qdrant for semantic retrieval."""
    client = _get_qdrant_client()
    if not client:
        return

    try:
        from qdrant_client.models import PointStruct

        if not await _ensure_qdrant_collection(client):
            return

        summary = engram.get("summary", "")
        if not summary:
            return

        embedding = await get_embedding(summary)
        point = PointStruct(
            id=uuid.uuid4().hex,
            vector=embedding,
            payload={
                "engram_id": engram_id,
                "user_id": engram.get("user_id", ""),
                "conversation_id": engram.get("conversation_id", ""),
                "summary": summary[:2000],
                "created_at": engram.get("created_at", datetime.now(timezone.utc)).isoformat(),
            },
        )
        client.upsert(collection_name=ENGRAM_COLLECTION, points=[point])

    except Exception as exc:
        logger.warning("Failed to index engram %s in Qdrant: %s", engram_id, exc)


async def search_engrams(
    query: str,
    user_id: str,
    limit: int = 3,
) -> list[dict]:
    """Search engrams via Qdrant for relevant long-term memory."""
    client = _get_qdrant_client()
    if not client:
        return []

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        embedding = await get_embedding(query)
        results = client.search(
            collection_name=ENGRAM_COLLECTION,
            query_vector=embedding,
            query_filter=Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            ),
            limit=limit,
            score_threshold=0.25,
        )
        return [
            {
                "score": hit.score,
                "summary": hit.payload.get("summary", ""),
                "conversation_id": hit.payload.get("conversation_id", ""),
                "engram_id": hit.payload.get("engram_id", ""),
            }
            for hit in results
        ]
    except Exception as exc:
        logger.warning("Qdrant engram search failed: %s", exc)
        return []
