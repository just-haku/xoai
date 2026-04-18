"""Pydantic schemas for MongoDB collections."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserDoc(BaseModel):
    username: str = ""
    email: Optional[str] = None
    password_hash: str
    name: str
    role: str = "user"  # admin | user
    status: str = "pending"  # pending | approved | disabled
    email_verified: bool = False
    quota_used_bytes: int = 0
    quota_limit_bytes: int = 5 * 1024 * 1024 * 1024  # Default 5GB
    lang: str = "EN"  # EN | VI
    active_work_chat_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SettingDoc(BaseModel):
    key: str  # e.g. "smtp", "agent_0_config", "fallback_pool", "tts_provider"
    value_encrypted: str  # Fernet-encrypted JSON string
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BotInstanceDoc(BaseModel):
    user_id: str
    platform: str  # discord | telegram | zalo
    token_encrypted: str
    status: str = "active"  # active | error | suspended
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApiKeyDoc(BaseModel):
    user_id: Optional[str] = None  # None = server fallback pool
    provider: str  # gemini | openai | anthropic | ollama
    key_encrypted: str
    is_fallback: bool = False
    rate_limit_reset_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationDoc(BaseModel):
    user_id: str
    channel: str = "web"  # web | zalo | telegram | discord
    title: str = "New Chat"
    summary_compressed: Optional[str] = None
    message_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MessageDoc(BaseModel):
    conversation_id: str
    role: str  # user | assistant | system
    content: str
    tool_calls: list = Field(default_factory=list)
    channel_metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TicketDoc(BaseModel):
    user_id: str
    subject: str = ""
    status: str = "open"  # open | triaging | resolved | closed
    agent_context: str = ""
    admin_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class McpServerDoc(BaseModel):
    name: str
    url: str
    transport: str = "stdio"  # stdio | sse
    user_id: Optional[str] = None  # None = global
    tools_cache: list = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RefreshSessionDoc(BaseModel):
    session_id: str
    user_id: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None
    ip: Optional[str] = None


class ProxyHandoffDoc(BaseModel):
    user_id: str
    role: str
    proxy_by: str
    session_id: str
    token_hash: str
    consumed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class BackgroundJobDoc(BaseModel):
    type: str
    status: str = "queued"
    attempts: int = 0
    max_attempts: int = 3
    payload: dict = Field(default_factory=dict)
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    run_after: datetime = Field(default_factory=datetime.utcnow)


class AgentProfileDoc(BaseModel):
    agent_key: str
    role: str
    display_name: str
    prompt_name: str
    provider: str
    model: str
    key: Optional[str] = None
    base_url: Optional[str] = None
    tool_allowlist: list[str] = Field(default_factory=list)
    risk_policy: dict = Field(default_factory=dict)
    enabled: bool = True
    max_concurrency: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UploadSessionDoc(BaseModel):
    upload_id: str
    user_id: str
    path: str
    filename: str
    upload_path: str
    chunk_size: int
    total_size: int = 0
    total_chunks: int = 0
    received_chunks: list[int] = Field(default_factory=list)
    received_bytes: int = 0
    status: str = "pending"
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StorageArtifactDoc(BaseModel):
    user_id: str
    path: str
    artifact_type: str
    retention_class: str
    pinned: bool = False
    job_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduledTaskDoc(BaseModel):
    name: str
    owner_user_id: str
    cron: str
    timezone: str = "UTC"
    enabled: bool = True
    agent_key: str
    workspace_scope: Optional[str] = None
    tool_policy: dict = Field(default_factory=dict)
    payload: dict = Field(default_factory=dict)
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskRunDoc(BaseModel):
    scheduled_task_id: str
    status: str = "queued"
    payload: dict = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryEngramDoc(BaseModel):
    user_id: str
    conversation_id: Optional[str] = None
    summary: str
    bullet_points: list[str] = Field(default_factory=list)
    source_message_ids: list[str] = Field(default_factory=list)
    freshness_score: float = 0.0
    confidence_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
