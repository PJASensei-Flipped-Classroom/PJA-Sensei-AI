"""Helpers for classifying LLM provider errors and rate-limit recovery.

Polityka 429: retry tego samego modelu po backoff → opcjonalny MAIN_MODEL_FALLBACK.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import MAIN_MODEL_FALLBACK

logger = logging.getLogger(__name__)

T = TypeVar("T")

RATE_LIMIT_BACKOFF_SECONDS = 1.5


def is_structured_output_unsupported(exc: BaseException) -> bool:
    """True when the provider rejects response_format / structured outputs."""
    text = str(exc).lower()
    return (
        "structured-outputs" in text
        or "structured_outputs" in text
        or (
            "response_format" in text
            and ("does not support" in text or "unsupported" in text)
        )
    )


def is_rate_limit_error(exc: BaseException) -> bool:
    """True when the provider signals HTTP 429 / rate limiting."""
    name = type(exc).__name__
    if name in {"RateLimitError", "APIRateLimitError"}:
        return True
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    text = str(exc).lower()
    return (
        "rate limit" in text
        or "rate-limited" in text
        or "rate_limited" in text
        or "error code: 429" in text
        or "'code': 429" in text
        or '"code": 429' in text
    )


def resolve_fallback_model(primary_model: str) -> str | None:
    """Secondary model after same-model 429 retry; None if disabled or identical."""
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
    """Try primary; on 429 wait and retry once; then optional MAIN_MODEL_FALLBACK.

    Returns ``(result, model_used)`` so callers can attribute the successful model
    (including after fallback).
    """
    delay = RATE_LIMIT_BACKOFF_SECONDS if backoff_seconds is None else backoff_seconds
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

    try:
        return await call(primary_model), primary_model
    except Exception as retry_exc:
        if not is_rate_limit_error(retry_exc):
            raise
        fallback = resolve_fallback_model(primary_model)
        if fallback is None:
            raise
        logger.warning(
            "Rate limit po retry na %s — przełączenie na fallback %s (%s)",
            primary_model,
            fallback,
            retry_exc,
        )
        return await call(fallback), fallback
