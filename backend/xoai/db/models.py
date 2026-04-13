"""Pydantic schemas for MongoDB collections."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserDoc(BaseModel):
    email: str
    password_hash: str
    name: str
    role: str = "user"  # admin | user
    status: str = "pending"  # pending | approved | disabled
    email_verified: bool = False
    quota_used_bytes: int = 0
    lang: str = "EN"  # EN | VI
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SettingDoc(BaseModel):
    key: str  # e.g. "smtp", "agent_0_config", "fallback_pool", "tts_provider"
    value_encrypted: str  # Fernet-encrypted JSON string
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
