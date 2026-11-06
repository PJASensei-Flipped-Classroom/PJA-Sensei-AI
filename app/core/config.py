from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    LLM_BASE_URL: str
    LLM_API_KEY: str
    MAIN_MODEL: str
    SECURITY_MODEL: str
    AI_AUTH_ENABLED: bool = True
    AI_JWT_SECRET: str = ""
    AI_JWT_AUDIENCE: Optional[str] = "pja-sensei-ai"
    AI_JWT_ISSUER: Optional[str] = "pja-spring"
    AI_EXPOSE_DOCS: bool = False
    AI_EXPOSE_UI: bool = False
    AI_EXPOSE_DEBUG: bool = False
    AI_PROFESSOR_ROLES: List[str] = ["professor", "admin"]
    RATE_LIMIT_PER_MINUTE: int = 60
    CONVERSATION_TTL_SECONDS: int = 7200
    CORS_ORIGINS: List[str] = []
    TRUST_X_FORWARDED_FOR: bool = False
    SECURITY_FAIL_CLOSED: bool = True
    SECURITY_ALWAYS_CLASSIFY: bool = False
    MAIN_MODEL_FALLBACK: Optional[str] = "qwen2.5-coder:3b"
    LLM_MAX_RETRIES: int = 2
    CACHE_SIZE: int = 128
    CACHE_TTL_SECONDS: int = 3600
    RAG_TOP_K: int = 3
    RAG_FETCH_TIMEOUT: float = 5.0
    RAG_FETCH_MAX_BYTES: int = 2_000_000
    FRUSTRATION_EVENT_COOLDOWN_SECONDS: float = 15.0

    TELEMETRY_URL: str = ""
    SUMMARY_WEBHOOK_URL: str = ""
    WEBHOOK_URL: str = ""
    WEBHOOK_TIMEOUT: float = 3.0
    WEBHOOK_EVENT_BUFFER_SIZE: int = 50

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Required LLM_* fields are filled from environment / .env (no code defaults by design).
# PyCharm flags Settings() as missing args; pydantic-settings loads them at runtime.
settings = Settings()  # type: ignore[call-arg]
