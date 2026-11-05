import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.api.auth import client_ip_from_request, extract_bearer_token, verify_access_token
from app.application.metrics import metrics
from app.core.config import settings


# OLD — broad public surface even with JWT on:
# _AUTH_OPEN_PREFIXES = (
#     "/health",
#     "/health_check",
#     "/metrics",
#     "/webhooks",
#     "/docs",
#     "/redoc",
#     "/openapi.json",
#     "/scenarios",
# )
# _AUTH_OPEN_EXACT = {"/", "/favicon.ico"}
# def _is_auth_open_path(path: str) -> bool:
#     if path in _AUTH_OPEN_EXACT:
#         return True
#     return any(path == prefix or path.startswith(prefix + "/") for prefix in _AUTH_OPEN_PREFIXES)
# Why: metrics, webhook buffer, OpenAPI, and lab UI leak ops data / attack maps if public.
# Wrong: JWT “on” still left those paths unauthenticated.
# Better: only health probes always open; UI/docs via AI_EXPOSE_* flags; metrics need JWT(+professor).

# Always public (load balancer / k8s probes).
_AUTH_OPEN_PREFIXES = (
    "/health",
    "/health_check",
)

_AUTH_OPEN_EXACT = {"/favicon.ico"}

# Paths subject to inbound IP rate limiting.
_RATE_LIMITED_PREFIXES = ("/conversations", "/config", "/validate-config")


def _is_auth_open_path(path: str) -> bool:
    if path in _AUTH_OPEN_EXACT:
        return True
    if any(path == prefix or path.startswith(prefix + "/") for prefix in _AUTH_OPEN_PREFIXES):
        return True
    # Dev/lab tester UI — only when explicitly exposed.
    if settings.AI_EXPOSE_UI and (path == "/" or path.startswith("/scenarios")):
        return True
    # OpenAPI — only when explicitly exposed.
    if settings.AI_EXPOSE_DOCS and path in {"/docs", "/redoc", "/openapi.json"}:
        return True
    return False


def _is_rate_limited_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in _RATE_LIMITED_PREFIXES)


class RequestIdMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        # OLD: dual header lookup was redundant (Starlette is case-insensitive)
        # incoming_id = request.headers.get("X-Request-Id") or request.headers.get("x-request-id")
        incoming_id = request.headers.get("X-Request-Id")
        request_id = incoming_id.strip() if (incoming_id and incoming_id.strip()) else str(uuid.uuid4())
        request.state.request_id = request_id

        metrics.inc_requests()
        response = await call_next(request)
        if response.status_code >= 400:
            metrics.inc_errors()
        response.headers["X-Request-Id"] = request_id
        return response


class JwtAuthMiddleware(BaseHTTPMiddleware):
    """Optional Bearer JWT gate controlled by AI_AUTH_ENABLED."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.AI_AUTH_ENABLED:
            return await call_next(request)

        if _is_auth_open_path(request.url.path):
            return await call_next(request)

        token = extract_bearer_token(request.headers.get("Authorization"))
        if not token:
            return JSONResponse(
                status_code=401,
                content={
                    "message_id": "unauthorized",
                    "detail": "Missing or invalid Authorization Bearer token.",
                },
            )

        ok, claims, error = verify_access_token(token)
        if not ok:
            return JSONResponse(
                status_code=401,
                content={
                    "message_id": "unauthorized",
                    "detail": error or "Unauthorized.",
                },
            )

        request.state.jwt_claims = claims
        return await call_next(request)


# Module-level store so tests can reset without rebuilding the app.
_rate_limit_hits: Dict[str, Deque[float]] = defaultdict(deque)
_RATE_LIMIT_WINDOW_SECONDS = 60.0


def reset_rate_limit_buckets() -> None:
    _rate_limit_hits.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Inbound per-IP sliding window using RATE_LIMIT_PER_MINUTE.
    Exceeding the limit returns intentional HTTP 429 with Retry-After.
    """

    def _prune(self, bucket: Deque[float], now: float) -> None:
        cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

    async def dispatch(self, request: Request, call_next) -> Response:
        limit = max(0, int(settings.RATE_LIMIT_PER_MINUTE))
        if limit <= 0 or not _is_rate_limited_path(request.url.path):
            return await call_next(request)

        client_host = request.client.host if request.client else None
        ip = client_ip_from_request(client_host, request.headers.get("X-Forwarded-For"))
        now = time.monotonic()
        bucket = _rate_limit_hits[ip]
        self._prune(bucket, now)

        if len(bucket) >= limit:
            retry_after = max(1, int(_RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0])) + 1)
            return JSONResponse(
                status_code=429,
                content={
                    "message_id": "rate_limit_exceeded",
                    "detail": f"Rate limit exceeded ({limit} requests per minute).",
                    "limit": limit,
                },
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)
