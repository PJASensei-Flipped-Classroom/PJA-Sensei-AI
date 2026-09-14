"""Application settings (pydantic-settings)."""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfiguracja runtime z zmiennych środowiskowych / pliku .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Free models (zero OpenRouter credits). Shared-pool 429 possible; avoid openrouter/free lottery.
    main_model: str = "google/gemma-4-31b-it:free"
    security_model: str = "liquid/lfm-2.5-2.6b:free"
    # Different provider than MAIN (not Google) so fallback survives Google shared-pool 429.
    main_model_fallback: str = "nex-agi/nex-n2.5-mini:free"

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


# Eksporty modułowe dla kodu legacy / adapterów — wartości z chwili importu.
_settings = get_settings()

OPENROUTER_API_KEY = _settings.openrouter_api_key
OPENROUTER_BASE_URL = _settings.openrouter_base_url
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
CACHE_TTL_SECONDS = _settings.cache_ttl_seconds
CACHE_MAX_ENTRIES = _settings.cache_max_entries
CONVERSATION_TTL = _settings.conversation_ttl
MAX_CONVERSATIONS = _settings.max_conversations
SECURITY_FAIL_CLOSED = _settings.security_fail_closed

# Reveal hint quota (session-scoped; not SenseiConfig — avoids IDE camelCase sync).
MAX_REVEALS_PER_SESSION = 3

_PLACEHOLDER_API_KEYS = frozenset(
    {
        "",
        "your_openrouter_api_key_here",
        "changeme",
        "replace_me",
    }
)


def openrouter_key_is_configured(api_key: str | None = None) -> bool:
    """True when a non-placeholder OpenRouter key is set."""
    key = (OPENROUTER_API_KEY if api_key is None else api_key) or ""
    key = key.strip()
    return bool(key) and key not in _PLACEHOLDER_API_KEYS
