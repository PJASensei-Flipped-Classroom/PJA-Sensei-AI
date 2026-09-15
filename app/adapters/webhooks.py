"""Wysyłka zdarzeń telemetrycznych i powiadomień webhook."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Mapping

import httpx

from app.core.config import TELEMETRY_URL

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(2.0, connect=1.0)
_DEFAULT_LIMITS = httpx.Limits(max_keepalive_connections=20, max_connections=50)

_client_lock = asyncio.Lock()
_telemetry_client: httpx.AsyncClient | None = None


async def get_telemetry_client() -> httpx.AsyncClient:
    """Zwraca lub bezpiecznie inicjalizuje współdzieloną pulę połączeń HTTP."""
    global _telemetry_client
    if _telemetry_client is None or _telemetry_client.is_closed:
        async with _client_lock:
            # Podwójne sprawdzenie wewnątrz sekcji krytycznej (double-checked locking)
            if _telemetry_client is None or _telemetry_client.is_closed:
                _telemetry_client = httpx.AsyncClient(
                    timeout=_DEFAULT_TIMEOUT,
                    limits=_DEFAULT_LIMITS,
                )
    return _telemetry_client


async def close_telemetry_client() -> None:
    """Zamyka współdzielonego klienta podczas wyłączania aplikacji (shutdown hook)."""
    global _telemetry_client
    async with _client_lock:
        if _telemetry_client is not None and not _telemetry_client.is_closed:
            await _telemetry_client.aclose()
            _telemetry_client = None


async def send_telemetry_webhook(
    payload: Mapping[str, Any],
    url: str | None = None,
    *,
    request_id: str = "-",
    client: httpx.AsyncClient | None = None,
) -> None:
    """Wysyła dane telemetryczne metodą POST w modelu fire-and-forget (nigdy nie rzuca wyjątku)."""
    endpoint = url or TELEMETRY_URL
    if not endpoint:
        return

    # Wzbogacenie metadanych o identyfikator żądania
    telemetry_payload = {**payload, "request_id": request_id}
    http_client = client or await get_telemetry_client()

    try:
        response = await http_client.post(endpoint, json=telemetry_payload)

        if response.is_success:
            logger.debug(
                "Telemetria POST %s -> status %s [request_id=%s]",
                endpoint,
                response.status_code,
                request_id,
            )
        else:
            logger.warning(
                "Telemetria POST %s -> błąd HTTP %s [request_id=%s]",
                endpoint,
                response.status_code,
                request_id,
            )
    except Exception as exc:
        # Tłumimy wszystkie błędy sieciowe (np. ConnectTimeout, DNS lookup failure),
        # aby błędy telemetrii nigdy nie przerywały głównej ścieżki wykonania biznesowego.
        logger.warning(
            "Nieudana wysyłka telemetrii do %s [request_id=%s]: %s",
            endpoint,
            request_id,
            exc,
        )