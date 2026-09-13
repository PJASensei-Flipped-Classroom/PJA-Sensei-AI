"""Outbound telemetry / summary webhooks."""

from __future__ import annotations

import logging

import httpx

from app.core.config import TELEMETRY_URL

logger = logging.getLogger(__name__)


async def send_telemetry_webhook(
    payload: dict,
    url: str | None = None,
    *,
    request_id: str = "-",
) -> None:
    target = url or TELEMETRY_URL
    payload = {**payload, "request_id": request_id}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(target, json=payload, timeout=2.0)
            logger.info(
                "Telemetry POST %s -> %s request_id=%s",
                target,
                resp.status_code,
                payload.get("request_id"),
            )
    except Exception as exc:
        logger.warning("Telemetry webhook failed (%s): %s", target, exc)
