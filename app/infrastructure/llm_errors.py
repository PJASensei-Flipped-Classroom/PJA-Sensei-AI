import time
from typing import Callable, TypeVar, Optional
from openai import RateLimitError, APIConnectionError, APITimeoutError, InternalServerError

T = TypeVar("T")

class LlmError(Exception):
    pass

class LlmRateLimitError(LlmError):
    pass

class LlmTransientError(LlmError):
    pass

def is_rate_limit_exception(exc: Exception) -> bool:
    if isinstance(exc, (LlmRateLimitError, RateLimitError)):
        return True
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    return "429" in str(exc) or "rate limit" in str(exc).lower()

def is_transient_exception(exc: Exception) -> bool:
    if isinstance(exc, (LlmTransientError, APIConnectionError, APITimeoutError, InternalServerError)):
        return True
    status_code = getattr(exc, "status_code", None)
    return status_code in (500, 502, 503, 504)

def execute_with_retry_and_fallback(fn: Callable[[Optional[str]], T], primary_model: str, fallback_model: Optional[str], max_retries: int = 2, backoff_seconds: float = 0.05) -> T:
    last_exc: Optional[Exception] = None
    current_model = primary_model

    for attempt in range(max_retries + 1):
        try:
            return fn(current_model)
        except Exception as exc:
            last_exc = exc
            if is_rate_limit_exception(exc):
                if fallback_model and current_model != fallback_model:
                    current_model = fallback_model
                    continue
                if attempt < max_retries:
                    time.sleep(backoff_seconds * (attempt + 1))
                    continue
                raise
            if is_transient_exception(exc) and attempt < max_retries:
                time.sleep(backoff_seconds * (attempt + 1))
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Nieoczekiwany błąd wywołania LLM")