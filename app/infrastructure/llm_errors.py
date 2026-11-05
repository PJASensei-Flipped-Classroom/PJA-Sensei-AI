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


class LlmUnavailableError(LlmError):
    """LLM connection/timeout exhausted after retries — map to HTTP 503."""

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
                # OLD: raise  # re-raised RateLimitError / OpenAI 429 as-is
                # Why: bare re-raise left OpenAI RateLimitError unmapped → clients saw raw 500/SDK errors.
                # Wrong: exhausted 429 after fallback was not a stable API contract.
                # Better: wrap as LlmRateLimitError so FastAPI returns HTTP 503 + message_id llm_rate_limited.
                raise LlmRateLimitError(str(exc)) from exc
            if is_transient_exception(exc) and attempt < max_retries:
                time.sleep(backoff_seconds * (attempt + 1))
                continue
            # OLD: raise  # re-raised APIConnectionError / timeout / other as-is
            # Why: connection/timeout after retries still bubbled as unhandled 500 (classroom fail when Ollama is down).
            # Wrong: APIConnectionError/APITimeoutError had no domain type / HTTP mapping.
            # Better: LlmUnavailableError → HTTP 503 + message_id llm_unavailable + Retry-After.
            if is_transient_exception(exc):
                raise LlmUnavailableError(str(exc)) from exc
            raise
    if last_exc:
        # OLD: raise last_exc
        # Why/wrong/better: same as above — normalize final exhausted error into typed LLM errors for handlers.
        if is_rate_limit_exception(last_exc):
            raise LlmRateLimitError(str(last_exc)) from last_exc
        if is_transient_exception(last_exc):
            raise LlmUnavailableError(str(last_exc)) from last_exc
        raise last_exc
    raise RuntimeError("Nieoczekiwany błąd wywołania LLM")
