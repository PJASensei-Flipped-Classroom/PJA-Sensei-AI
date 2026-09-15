"""Application settings (pydantic-settings)."""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfiguracja runtime z zmiennych środowiskowych / pliku .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # OpenAI-compatible endpoint (Ollama / LM Studio).
    llm_base_url: str = Field(
        default="http://127.0.0.1:11434/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "BASE_URL"),
    )
    llm_api_key: str = Field(
        default="ollama",
        validation_alias=AliasChoices("LLM_API_KEY", "API_KEY"),
    )
    main_model: str = Field(
        default="qwen2.5-coder:7b",
        validation_alias=AliasChoices("MAIN_MODEL", "MODEL"),
    )
    security_model: str = "qwen2.5-coder:7b"
    # Optional second model after provider 429 (usually empty for local Ollama).
    main_model_fallback: str = ""

    telemetry_url: str = ""
    summary_webhook_url: str | None = None

    cors_origins: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5500,http://127.0.0.1:5500,null"
    )

    ai_auth_enabled: bool = False
    ai_jwt_secret: str = ""
    ai_jwt_algorithm: str = "HS256"

    rate_limit_per_minute: int = 30
    # Gdy False (domyślnie lokalnie), X-Forwarded-For jest ignorowane — bez spoofingu limitu.
    trust_x_forwarded_for: bool = False
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
    """Zwraca singleton Settings (cache'owany na czas życia procesu)."""
    return Settings()


# Eksporty modułowe — wartości z chwili importu.
_settings = get_settings()

LLM_BASE_URL = _settings.llm_base_url
LLM_API_KEY = _settings.llm_api_key
MAIN_MODEL = _settings.main_model
SECURITY_MODEL = _settings.security_model
MAIN_MODEL_FALLBACK = _settings.main_model_fallback
TELEMETRY_URL = _settings.telemetry_url
SUMMARY_WEBHOOK_URL = _settings.resolved_summary_webhook_url
CORS_ORIGINS = _settings.cors_origin_list
AI_AUTH_ENABLED = _settings.ai_auth_enabled
AI_JWT_SECRET = _settings.ai_jwt_secret
AI_JWT_ALGORITHM = _settings.ai_jwt_algorithm
RATE_LIMIT_PER_MINUTE = _settings.rate_limit_per_minute
TRUST_X_FORWARDED_FOR = _settings.trust_x_forwarded_for
CACHE_TTL_SECONDS = _settings.cache_ttl_seconds
CACHE_MAX_ENTRIES = _settings.cache_max_entries
CONVERSATION_TTL = _settings.conversation_ttl
MAX_CONVERSATIONS = _settings.max_conversations
SECURITY_FAIL_CLOSED = _settings.security_fail_closed

MAX_REVEALS_PER_SESSION = 3

_PLACEHOLDER_API_KEYS = frozenset(
    {
        "",
        "changeme",
        "replace_me",
    }
)


def llm_is_configured(api_key: str | None = None) -> bool:
    """True when LLM API key is set (``ollama`` / ``lm-studio`` count as configured)."""
    key = (LLM_API_KEY if api_key is None else api_key) or ""
    key = key.strip()
    return bool(key) and key not in _PLACEHOLDER_API_KEYS
