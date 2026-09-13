"""Request-id middleware and context."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request_id_var.set(rid)
        request.state.request_id = rid
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response
