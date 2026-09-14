"""In-memory sliding-window rate limiter with background cleanup."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from app.core.config import RATE_LIMIT_PER_MINUTE
from app.core.metrics import metrics

WINDOW_SECONDS = 60.0


@dataclass(frozen=True)
class RateLimitResult:
    """Wynik próby zajęcia slotu w oknie rate-limitu."""

    allowed: bool
    retry_after: int = 0


class SlidingWindowRateLimiter:
    """Wątkowo-bezpieczny limiter częstotliwości zapytań (Sliding Window Log)."""

    def __init__(self, limit: int = RATE_LIMIT_PER_MINUTE, window_seconds: float = WINDOW_SECONDS) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str) -> RateLimitResult:
        """Sprawdza dostępność slotu w oknie i rejestruje uderzenie."""
        now = time.monotonic()

        with self._lock:
            window = self._hits.setdefault(key, deque())

            # Usuwanie przeterminowanych wpisów z początku kolejki O(1)
            while window and (now - window[0]) > self.window_seconds:
                window.popleft()

            if len(window) >= self.limit:
                retry_after = max(1, math.ceil(self.window_seconds - (now - window[0])))
                return RateLimitResult(allowed=False, retry_after=retry_after)

            window.append(now)
            return RateLimitResult(allowed=True)

    def cleanup_stale_buckets(self) -> int:
        """Czyści nieaktywne koszyki (wywoływane w tle)."""
        now = time.monotonic()
        with self._lock:
            stale_keys = [
                k for k, win in self._hits.items()
                if not win or (now - win[-1]) > self.window_seconds
            ]
            for k in stale_keys:
                del self._hits[k]
            return len(stale_keys)


rate_limiter = SlidingWindowRateLimiter()


def resolve_client_key(request: Request, conversation_id: str | None = None) -> str:
    """Wyznacza bezpieczny identyfikator koszyka limitowania."""
    if conversation_id:
        return f"conv:{conversation_id}"

    # W środowisku za zaufanym reverse-proxy bierzemy pierwszy publiczny adres
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        return f"ip:{client_ip}"

    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


def enforce_rate_limit(request: Request, conversation_id: str | None = None) -> None:
    """Zależność FastAPI egzekwująca limit zapytań i rzucająca błąd HTTP 429."""
    key = resolve_client_key(request, conversation_id)
    result = rate_limiter.acquire(key)

    if not result.allowed:
        metrics.inc("rate_limited")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
            headers={"Retry-After": str(result.retry_after)},
        )