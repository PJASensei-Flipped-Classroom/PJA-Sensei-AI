"""Shared telemetry helpers for API routers (binds request_id from context)."""

from __future__ import annotations

from typing import Any, Mapping

from app.adapters.webhooks import send_telemetry_webhook
from app.api.middleware import request_id_var


async def send_request_telemetry(
    payload: Mapping[str, Any],
    url: str | None = None,
    *,
    request_id: str | None = None,
) -> None:
    """Fire-and-forget webhook with X-Request-Id from middleware context."""
    await send_telemetry_webhook(
        payload,
        url=url,
        request_id=request_id if request_id is not None else request_id_var.get("-"),
    )
