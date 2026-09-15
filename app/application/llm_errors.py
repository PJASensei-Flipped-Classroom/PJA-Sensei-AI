"""Klasyfikacja błędów dostawcy LLM oraz polityka ponawiania prób po przekroczeniu limitów (HTTP 429)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import TypeVar

from app.core.config import MAIN_MODEL_FALLBACK

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_BACKOFF_SECONDS = 1.5
# Alias używany w testach / starszych monkeypatchach
RATE_LIMIT_BACKOFF_SECONDS = DEFAULT_BACKOFF_SECONDS

_RATE_LIMIT_ERROR_CLASSES = frozenset({"RateLimitError", "APIRateLimitError"})
_RATE_LIMIT_PATTERNS = (
    "rate limit",
    "rate-limited",
    "rate_limited",
    "error code: 429",
    "'code': 429",
    '"code": 429',
)

_STRUCTURED_OUTPUT_PATTERNS = (
    "structured-outputs",
    "structured_outputs",
)


def is_structured_output_unsupported(exc: BaseException) -> bool:
    """Sprawdza, czy dostawca LLM odrzucił żądanie ze względu na brak obsługi response_format."""
    text = str(exc).lower()
    if any(pattern in text for pattern in _STRUCTURED_OUTPUT_PATTERNS):
        return True

    return "response_format" in text and ("does not support" in text or "unsupported" in text)


def is_rate_limit_error(exc: BaseException) -> bool:
    """Sprawdza, czy wyjątek oznacza przekroczenie limitu wywołań (HTTP 429 / Rate Limit)."""
    if type(exc).__name__ in _RATE_LIMIT_ERROR_CLASSES:
        return True

    if getattr(exc, "status_code", None) == 429:
        return True

    # KeyError z metryk zawiera w repr listę dozwolonych kluczy (m.in. rate_limited)
    # i nie może być mylony z 429 dostawcy.
    if isinstance(exc, KeyError):
        return False

    text = str(exc).lower()
    return any(pattern in text for pattern in _RATE_LIMIT_PATTERNS)


def resolve_fallback_model(primary_model: str) -> str | None:
    """Zwraca model zapasowy (fallback); zwraca None, jeśli fallback wyłączono lub jest identyczny z bazowym."""
    fallback = (MAIN_MODEL_FALLBACK or "").strip()
    if not fallback or fallback == primary_model:
        return None
    return fallback


async def call_with_rate_limit_policy(
    primary_model: str,
    call: Callable[[str], Awaitable[T]],
    *,
    backoff_seconds: float | None = None,
) -> tuple[T, str]:
    """Wykonuje wywołanie modelu z polityką: model główny -> retry po backoffie -> model awaryjny."""
    delay = RATE_LIMIT_BACKOFF_SECONDS if backoff_seconds is None else backoff_seconds
    # 1. Próba wykonania na modelu podstawowym
    try:
        return await call(primary_model), primary_model
    except Exception as first_exc:
        if not is_rate_limit_error(first_exc):
            raise

        logger.warning(
            "Rate limit na modelu %s — ponowienie za %.1fs (%s)",
            primary_model,
            delay,
            first_exc,
        )
        await asyncio.sleep(delay)

    # 2. Ponowna próba (retry) na modelu podstawowym
    try:
        return await call(primary_model), primary_model
    except Exception as retry_exc:
        if not is_rate_limit_error(retry_exc):
            raise

        fallback_model = resolve_fallback_model(primary_model)
        if fallback_model is None:
            raise

        logger.warning(
            "Rate limit po retry na %s — przełączenie na fallback %s (%s)",
            primary_model,
            fallback_model,
            retry_exc,
        )
        # 3. Ostateczna próba na modelu rezerwowym
        return await call(fallback_model), fallback_model
