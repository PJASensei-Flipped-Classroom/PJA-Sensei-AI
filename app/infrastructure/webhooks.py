import logging
import time
from typing import Dict, Any, Optional, Callable, List
import httpx
from app.domain.ports import WebhookPort
from app.core.config import settings

logger = logging.getLogger(__name__)

class HttpWebhookAdapter(WebhookPort):
    def __init__(self, sender: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.sender = sender
        self.sent_events: List[Dict[str, Any]] = []

    def _resolve_target_url(self, event_type: str) -> str:
        if event_type == "session_summary":
            return (
                    getattr(settings, "SUMMARY_WEBHOOK_URL", "")
                    or getattr(settings, "TELEMETRY_URL", "")
                    or getattr(settings, "WEBHOOK_URL", "")
                    or ""
            ).strip()
        return (
                getattr(settings, "TELEMETRY_URL", "")
                or getattr(settings, "WEBHOOK_URL", "")
                or ""
        ).strip()

    def send_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        try:
            envelope = {
                "event": event_type,
                "timestamp": time.time(),
                **payload,
            }
            target_url = self._resolve_target_url(event_type)

            self.sent_events.append({"url": target_url, "payload": envelope})

            if self.sender is not None:
                self.sender(target_url, envelope)
                return True

            if not target_url:
                return False

            with httpx.Client(timeout=getattr(settings, "WEBHOOK_TIMEOUT", 3.0)) as client:
                response = client.post(target_url, json=envelope)
                response.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("Webhook '%s' failed (fire-and-forget ignored): %s", event_type, exc)
            return False