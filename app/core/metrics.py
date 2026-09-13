"""In-process metrics for the AI microservice."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

METRIC_PREFIX = "pja_sensei"


@dataclass
class MetricsCollector:
    requests_total: int = 0
    messages_total: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    penalties_total: int = 0
    tokens_total: int = 0
    rate_limited: int = 0
    llm_errors: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            current = getattr(self, name, None)
            if isinstance(current, (int, float)):
                setattr(self, name, current + amount)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            hits = self.cache_hits
            misses = self.cache_misses
            denom = hits + misses
            msg_total = self.messages_total

            return {
                "requests_total": self.requests_total,
                "messages_total": msg_total,
                "cache_hits": hits,
                "cache_misses": misses,
                "cache_hit_rate": round(hits / denom, 3) if denom else 0.0,
                "penalties_total": self.penalties_total,
                "tokens_total": self.tokens_total,
                "avg_tokens_per_message": round(self.tokens_total / msg_total, 1) if msg_total else 0.0,
                "rate_limited": self.rate_limited,
                "llm_errors": self.llm_errors,
            }

    def prometheus_text(self, extra: dict[str, Any] | None = None) -> str:
        snap = self.snapshot()
        if extra:
            snap.update(extra)

        definitions = [
            ("requests_total", "requests_total", "counter", "Total HTTP-tracked requests"),
            ("messages_total", "messages_total", "counter", "Total chat messages processed"),
            ("cache_hits", "cache_hits_total", "counter", "Exact-match cache hits"),
            ("cache_misses", "cache_misses_total", "counter", "Exact-match cache misses"),
            ("penalties_total", "penalties_total", "counter", "Code-reveal / rule penalties"),
            ("tokens_total", "tokens_total", "counter", "Estimated tokens used"),
            ("rate_limited", "rate_limited_total", "counter", "Rate-limit rejections"),
            ("llm_errors", "llm_errors_total", "counter", "LLM call failures"),
            ("conversations", "conversations", "gauge", "Active in-memory conversations"),
            ("cache_size", "cache_size", "gauge", "Exact-match cache entries"),
        ]

        lines: list[str] = []
        for key, metric_suffix, metric_type, help_text in definitions:
            if key in snap:
                metric_name = f"{METRIC_PREFIX}_{metric_suffix}"
                lines.extend([
                    f"# HELP {metric_name} {help_text}",
                    f"# TYPE {metric_name} {metric_type}",
                    f"{metric_name} {snap[key]}",
                ])

        return "\n".join(lines) + "\n"


metrics = MetricsCollector()