import logging
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

import httpx

from app.application.metrics import metrics
from app.core.config import settings
from app.domain.ports import WebhookPort

logger = logging.getLogger(__name__)


class HttpWebhookAdapter(WebhookPort):
    def __init__(self, sender: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.sender = sender
        # OLD: self.sent_events: List[Dict[str, Any]] = []
        # Removed because: unbounded list grew forever; recent_events (bounded deque) is enough for /webhooks/recent.
        buf = max(1, int(getattr(settings, "WEBHOOK_EVENT_BUFFER_SIZE", 50) or 50))
        self.recent_events: Deque[Dict[str, Any]] = deque(maxlen=buf)

    @staticmethod
    def _resolve_target_url(event_type: str) -> str:
        if event_type == "session_summary":
            return (
                settings.SUMMARY_WEBHOOK_URL
                or settings.TELEMETRY_URL
                or settings.WEBHOOK_URL
                or ""
            ).strip()
        return (settings.TELEMETRY_URL or settings.WEBHOOK_URL or "").strip()

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        items = list(self.recent_events)
        if limit <= 0:
            return items
        return items[-limit:]

    def send_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        try:
            envelope = {
                "event": event_type,
                "timestamp": time.time(),
                **payload,
            }
            target_url = self._resolve_target_url(event_type)

            record = {"url": target_url, "payload": envelope}
            # OLD: self.sent_events.append(record)
            # Removed because: duplicate of recent_events with no reader and no max length.
            self.recent_events.append(record)

            if self.sender is not None:
                self.sender(target_url, envelope)
                metrics.inc_webhook(True)
                return True

            if not target_url:
                metrics.inc_webhook(False)
                return False

            with httpx.Client(timeout=settings.WEBHOOK_TIMEOUT) as client:
                response = client.post(target_url, json=envelope)
                response.raise_for_status()
            metrics.inc_webhook(True)
            return True
        except Exception as exc:
            metrics.inc_webhook(False)
            logger.warning("Webhook '%s' failed (fire-and-forget ignored): %s", event_type, exc)
            return False
