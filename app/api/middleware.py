"""Request-id middleware and contextvars tracking (High-performance Pure ASGI)."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Bezpieczny wzorzec dla identyfikatora: litery, cyfry, myślniki i podkreślenia (max 64 znaki)
_SAFE_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class RequestIdMiddleware:
    """Wysokowydajny middleware ASGI do śledzenia korelacji żądań bez narzutu BaseHTTPMiddleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Pobranie lub wygenerowanie bezpiecznego identyfikatora
        incoming_rid = None
        for key, value in scope.get("headers", []):
            if key.lower() == b"x-request-id":
                decoded = value.decode("latin1").strip()
                if _SAFE_REQUEST_ID_RE.match(decoded):
                    incoming_rid = decoded
                break

        rid = incoming_rid or str(uuid.uuid4())

        # 2. Ustawienie zmiennej kontekstowej z gwarancją posprzątania
        token = request_id_var.set(rid)

        # Zapis do stanu żądania (dostępnego w request.state w FastAPI)
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = rid

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", rid.encode("latin1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id_var.reset(token)