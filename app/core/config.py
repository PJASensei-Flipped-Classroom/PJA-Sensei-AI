"""Application settings (pydantic-settings)."""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    main_model: str = "meta-llama/llama-3.3-70b-instruct"
    security_model: str = "meta-llama/llama-3.1-8b-instruct"

    telemetry_url: str = "http://localhost:8080/api/ai/telemetry"
    summary_webhook_url: str | None = None

    cors_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5500,http://127.0.0.1:5500,null"
    )

    ai_auth_enabled: bool = False
    ai_jwt_secret: str = ""
    ai_jwt_algorithm: str = "HS256"

    rate_limit_per_minute: int = 30
    cache_ttl_seconds: int = 30 * 60
    cache_max_entries: int = 500
    conversation_ttl_seconds: int = 2 * 3600
    max_conversations: int = 200
    security_fail_closed: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def conversation_ttl(self) -> timedelta:
        return timedelta(seconds=self.conversation_ttl_seconds)

    @property
    def resolved_summary_webhook_url(self) -> str:
        return self.summary_webhook_url or self.telemetry_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


_settings = get_settings()

OPENROUTER_API_KEY = _settings.openrouter_api_key
OPENROUTER_BASE_URL = _settings.openrouter_base_url
MAIN_MODEL = _settings.main_model
SECURITY_MODEL = _settings.security_model
TELEMETRY_URL = _settings.telemetry_url
SUMMARY_WEBHOOK_URL = _settings.resolved_summary_webhook_url
CORS_ORIGINS = _settings.cors_origin_list
AI_AUTH_ENABLED = _settings.ai_auth_enabled
AI_JWT_SECRET = _settings.ai_jwt_secret
AI_JWT_ALGORITHM = _settings.ai_jwt_algorithm
RATE_LIMIT_PER_MINUTE = _settings.rate_limit_per_minute
CACHE_TTL_SECONDS = _settings.cache_ttl_seconds
CACHE_MAX_ENTRIES = _settings.cache_max_entries
CONVERSATION_TTL = _settings.conversation_ttl
MAX_CONVERSATIONS = _settings.max_conversations
SECURITY_FAIL_CLOSED = _settings.security_fail_closed