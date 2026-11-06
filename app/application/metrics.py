from threading import Lock
from typing import Dict


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self.requests_total = 0
        self.errors_total = 0
        self.llm_rate_limited_total = 0
        self.messages_total = 0
        self.webhooks_sent_total = 0
        self.webhooks_failed_total = 0

    def inc_requests(self) -> None:
        with self._lock:
            self.requests_total += 1

    def inc_errors(self) -> None:
        with self._lock:
            self.errors_total += 1

    def inc_llm_rate_limited(self) -> None:
        with self._lock:
            self.llm_rate_limited_total += 1

    def inc_messages(self) -> None:
        with self._lock:
            self.messages_total += 1

    def inc_webhook(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self.webhooks_sent_total += 1
            else:
                self.webhooks_failed_total += 1

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return {
                "requests_total": self.requests_total,
                "errors_total": self.errors_total,
                "llm_rate_limited_total": self.llm_rate_limited_total,
                "messages_total": self.messages_total,
                "webhooks_sent_total": self.webhooks_sent_total,
                "webhooks_failed_total": self.webhooks_failed_total,
            }


metrics = MetricsRegistry()
