from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    LLM_BASE_URL: str
    LLM_API_KEY: str
    MAIN_MODEL: str
    SECURITY_MODEL: str
    AI_AUTH_ENABLED: bool = False
    AI_JWT_SECRET: str = ""
    RATE_LIMIT_PER_MINUTE: int = 60
    CACHE_SIZE: int = 1000
    CACHE_TTL: int = 60*60
    CONVERSATION_TTL_SECONDS: int = 7200
    TELEMETRY_URL: str = ""
    SUMMARY_WEBHOOK_URL: str = ""
    CORS_ORIGINS: List[str] = ["*"]
    TRUST_X_FORWARDED_FOR: bool = True
    SECURITY_FAIL_CLOSED: bool = True
    MAIN_MODEL_FALLBACK: Optional[str] = "qwen2.5-coder:3b"
    LLM_MAX_RETRIES: int = 2

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
settings = Settings()