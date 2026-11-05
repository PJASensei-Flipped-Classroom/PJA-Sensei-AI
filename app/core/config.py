from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    LLM_BASE_URL: str
    LLM_API_KEY: str
    MAIN_MODEL: str
    SECURITY_MODEL: str
    # OLD (dev-open defaults):
    # AI_AUTH_ENABLED: bool = False
    # AI_JWT_SECRET: str = ""
    # CORS_ORIGINS: List[str] = ["*"]
    # TRUST_X_FORWARDED_FOR: bool = True
    # Why: production-safe defaults if .env is missing keys.
    # Wrong: auth off + CORS * + trusting XFF made a mis-deploy fully open and rate-limit spoofable.
    # Better: auth on, empty CORS, XFF off by default; local .env can still open the playground.
    AI_AUTH_ENABLED: bool = True
    AI_JWT_SECRET: str = ""
    AI_JWT_AUDIENCE: Optional[str] = "pja-sensei-ai"
    AI_JWT_ISSUER: Optional[str] = "pja-spring"
    AI_EXPOSE_DOCS: bool = False
    AI_EXPOSE_UI: bool = False
    AI_PROFESSOR_ROLES: List[str] = ["professor", "admin"]
    RATE_LIMIT_PER_MINUTE: int = 60
    CONVERSATION_TTL_SECONDS: int = 7200
    CORS_ORIGINS: List[str] = []
    TRUST_X_FORWARDED_FOR: bool = False
    SECURITY_FAIL_CLOSED: bool = True
    # When true, every message is also checked by SECURITY_MODEL (costly).
    SECURITY_ALWAYS_CLASSIFY: bool = False
    MAIN_MODEL_FALLBACK: Optional[str] = "qwen2.5-coder:3b"
    LLM_MAX_RETRIES: int = 2
    CACHE_SIZE: int = 128
    CACHE_TTL_SECONDS: int = 3600
    RAG_TOP_K: int = 3
    RAG_FETCH_TIMEOUT: float = 5.0
    # OLD: no fetch body cap
    # Why: unbounded RAG downloads can fill RAM / stall workers.
    # Wrong: a large PDF/HTML page was fully buffered before decode.
    # Better: truncate fetch bodies (default 2 MB) and log truncation.
    RAG_FETCH_MAX_BYTES: int = 2_000_000
    # Minimum seconds between frustration_streak increments (anti hint-farming).
    # OLD: no cooldown on IDE events
    # Why: students could POST compile_error/test_failed twice and unlock hints immediately.
    # Wrong: frustration_streak had no rate limit — hint farming via /events.
    # Better: ignore streak increments inside this cooldown window (events still recorded).
    FRUSTRATION_EVENT_COOLDOWN_SECONDS: float = 15.0

    TELEMETRY_URL: str = ""
    SUMMARY_WEBHOOK_URL: str = ""
    WEBHOOK_URL: str = ""
    WEBHOOK_TIMEOUT: float = 3.0
    WEBHOOK_EVENT_BUFFER_SIZE: int = 50

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
settings = Settings()
