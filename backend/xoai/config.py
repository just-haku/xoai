from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Minimal settings — only essentials from .env.
    Everything else (SMTP, API keys, tokens) lives in MongoDB `settings` collection.
    """

    mongo_uri: str = "mongodb://xoai-mongo:27017/xoai"
    redis_url: str = "redis://xoai-redis:6379/0"
    secret_key: str = "change-me"
    xoai_storage: str = "/app/storage"
    public_base_url: str = "http://localhost:3080"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
