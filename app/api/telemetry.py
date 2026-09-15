"""Pomocnicze funkcje telemetrii dla warstwy API (automatyczne wiązanie request_id z kontekstu)."""

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
    """Wysyła asynchroniczny webhook telemetryczny z powiązanym identyfikatorem śledzenia (Request-ID)."""
    resolved_request_id = request_id or request_id_var.get("-")

    await send_telemetry_webhook(
        payload=payload,
        url=url,
        request_id=resolved_request_id,
    )