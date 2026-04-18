from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


DEFAULT_SECRET_KEY = "development-secret-key-change-me-1234567890"
WEAK_SECRET_KEYS = {
    "",
    "change-me",
    "secret",
    "default",
    "development-secret",
    DEFAULT_SECRET_KEY,
}


class Settings(BaseSettings):
    """Runtime settings loaded from environment."""

    mongo_uri: str = "mongodb://xoai-mongo:27017/xoai"
    redis_url: str = "redis://xoai-redis:6379/0"
    secret_key: str = DEFAULT_SECRET_KEY
    xoai_storage: str = "/app/storage"
    public_base_url: str = "http://localhost:3080"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3080", "http://127.0.0.1:3080"]
    )
    enable_cors: bool = False
    admin_workspace_path: str | None = None
    max_upload_bytes: int = 5 * 1024 * 1024 * 1024
    max_avatar_bytes: int = 2 * 1024 * 1024
    max_editor_bytes: int = 5 * 1024 * 1024
    upload_chunk_bytes: int = 8 * 1024 * 1024
    upload_session_ttl_hours: int = 24
    transient_file_ttl_days: int = 7
    gc_batch_size: int = 200
    restart_jitter_seconds: int = 20
    query_tool_failure_threshold: int = 10
    query_max_tool_steps: int = 16
    qdrant_url: str = "http://xoai-qdrant:6333"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return ["http://localhost:3080", "http://127.0.0.1:3080"]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return value
        raise TypeError("cors_origins must be a comma-separated string or a list")


settings = Settings()


def has_strong_secret_key(secret_key: str) -> bool:
    if secret_key in WEAK_SECRET_KEYS:
        return False
    return len(secret_key) >= 32


def validate_runtime_settings() -> None:
    if not has_strong_secret_key(settings.secret_key):
        raise RuntimeError(
            "SECRET_KEY is unset, default, or too weak. Provide a strong secret key with at least 32 characters."
        )
