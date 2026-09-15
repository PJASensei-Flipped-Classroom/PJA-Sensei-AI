"""Wysokowydajny middleware ASGI do śledzenia identyfikatora korelacji (Request-ID)."""

from __future__ import annotations

from contextvars import ContextVar
import re
from typing import Any
import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Bezpieczny wzorzec: litery, cyfry, łączniki i podkreślenia (od 1 do 64 znaków)
_SAFE_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _extract_valid_request_id(headers: list[tuple[bytes, bytes]]) -> str | None:
    """Wyszukuje nagłówek x-request-id w nagłówkach ASGI i waliduje jego format."""
    for name, raw_value in headers:
        if name.lower() == b"x-request-id":
            decoded = raw_value.decode("latin1").strip()
            if _SAFE_REQUEST_ID_PATTERN.match(decoded):
                return decoded
            break
    return None


class RequestIdMiddleware:
    """Niskopoziomowy komponent ASGI dodający Request-ID bez narzutu BaseHTTPMiddleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Przekazujemy protokoły nie-HTTP (np. lifespany, websockety) bez modyfikacji
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        request_id = _extract_valid_request_id(headers) or str(uuid.uuid4())

        # Ustawienie zmiennej kontekstowej dla asynchronicznego stosu wywołań
        context_token = request_id_var.set(request_id)

        # Zapis do scope['state'], aby identyfikator był dostępny w request.state w FastAPI
        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        async def send_with_request_id(message: dict[str, Any]) -> None:
            """Wstrzykuje nagłówek X-Request-ID do odpowiedzi HTTP tuż przed jej wysłaniem."""
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", request_id.encode("latin1")))
                message["headers"] = response_headers

            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            # Gwarantowane przywrócenie poprzedniej wartości tokenu (ochrona przed wyciekami kontekstu)
            request_id_var.reset(context_token)