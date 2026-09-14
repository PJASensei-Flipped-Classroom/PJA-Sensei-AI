"""Outbound telemetry / summary webhooks."""

from __future__ import annotations

import logging
from typing import Any, Mapping

import httpx

from app.core.config import TELEMETRY_URL

logger = logging.getLogger(__name__)

_TELEMETRY_CLIENT: httpx.AsyncClient | None = None


def get_telemetry_client() -> httpx.AsyncClient:
    """Return or create the shared HTTP client for telemetry."""
    global _TELEMETRY_CLIENT
    if _TELEMETRY_CLIENT is None or _TELEMETRY_CLIENT.is_closed:
        _TELEMETRY_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(2.0, connect=1.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _TELEMETRY_CLIENT


async def close_telemetry_client() -> None:
    """Close shared client on app shutdown."""
    global _TELEMETRY_CLIENT
    if _TELEMETRY_CLIENT is not None and not _TELEMETRY_CLIENT.is_closed:
        await _TELEMETRY_CLIENT.aclose()
        _TELEMETRY_CLIENT = None


async def send_telemetry_webhook(
    payload: Mapping[str, Any],
    url: str | None = None,
    *,
    request_id: str = "-",
    client: httpx.AsyncClient | None = None,
) -> None:
    """POST telemetry JSON; never raises to the caller."""
    target = url or TELEMETRY_URL
    if not target:
        return

    data = {**payload, "request_id": request_id}
    http_client = client or get_telemetry_client()

    try:
        resp = await http_client.post(target, json=data)
        if resp.is_success:
            logger.debug(
                "Telemetry POST %s -> %s [request_id=%s]",
                target,
                resp.status_code,
                request_id,
            )
        else:
            logger.warning(
                "Telemetry POST %s returned HTTP %s [request_id=%s]",
                target,
                resp.status_code,
                request_id,
            )
    except Exception as exc:
        logger.warning(
            "Telemetry POST failed %s [request_id=%s]: %s",
            target,
            request_id,
            exc,
        )
