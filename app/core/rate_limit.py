from __future__ import annotations

import math
import threading
import time
from collections import deque

from fastapi import HTTPException, Request, status

from app.core.config import RATE_LIMIT_PER_MINUTE
from app.core.metrics import metrics

WINDOW_SECONDS = 60.0


class RateLimiter:
    def __init__(self, limit_per_minute: int = RATE_LIMIT_PER_MINUTE):
        self.limit = limit_per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()

        with self._lock:
            window = self._hits.get(key)
            if window is None:
                window = deque()
                self._hits[key] = window

            while window and (now - window[0]) > WINDOW_SECONDS:
                window.popleft()

            if len(window) >= self.limit:
                metrics.inc("rate_limited")
                retry_after = max(1, math.ceil(WINDOW_SECONDS - (now - window[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )

            window.append(now)

            if len(self._hits) > 10_000:
                self._cleanup_stale_keys(now)

    def _cleanup_stale_keys(self, now: float) -> None:
        stale_keys = [
            k for k, win in self._hits.items()
            if not win or (now - win[-1]) > WINDOW_SECONDS
        ]
        for k in stale_keys:
            del self._hits[k]


rate_limiter = RateLimiter()


def client_key(request: Request, conversation_id: str | None = None) -> str:
    """Rate-limit bucket: conversation id if present, else client IP."""
    if conversation_id:
        return f"conv:{conversation_id}"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        return f"ip:{client_ip}"

    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"