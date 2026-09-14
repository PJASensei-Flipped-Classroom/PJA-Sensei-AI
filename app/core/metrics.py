"""In-process metrics for the AI microservice."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Final

METRIC_PREFIX: Final[str] = "pja_sensei"

_ALLOWED_COUNTERS: Final[frozenset[str]] = frozenset({
    "requests_total",
    "messages_total",
    "cache_hits",
    "cache_misses",
    "penalties_total",
    "tokens_total",
    "rate_limited",
    "llm_errors",
    "llm_rate_limited",
})


@dataclass(slots=True)
class MetricsCollector:
    """Wątkowo-bezpieczny kolektor metryk wewnętrznych procesu."""

    requests_total: int = 0
    messages_total: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    penalties_total: int = 0
    tokens_total: int = 0
    rate_limited: int = 0
    llm_errors: int = 0
    llm_rate_limited: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, name: str, amount: int = 1) -> None:
        """Inkrementuje licznik o zadaną wartość, weryfikując poprawność klucza."""
        if name not in _ALLOWED_COUNTERS:
            raise KeyError(f"Nieznana metryka: {name}. Dozwolone: {_ALLOWED_COUNTERS}")

        with self._lock:
            current = getattr(self, name)
            setattr(self, name, current + amount)

    def snapshot(self) -> dict[str, Any]:
        """Zwraca spójny słownik metryk w formacie JSON."""
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
                "llm_rate_limited": self.llm_rate_limited,
            }

    def prometheus_text(self, extra: dict[str, Any] | None = None) -> str:
        """Formatuje metryki w oficjalnym formacie tekstowym Prometheus v0.0.4."""
        snap = self.snapshot()
        if extra:
            snap.update(extra)

        definitions: tuple[tuple[str, str, str, str], ...] = (
            ("requests_total", "requests_total", "counter", "Total HTTP-tracked requests"),
            ("messages_total", "messages_total", "counter", "Total chat messages processed"),
            ("cache_hits", "cache_hits_total", "counter", "Exact-match cache hits"),
            ("cache_misses", "cache_misses_total", "counter", "Exact-match cache misses"),
            ("penalties_total", "penalties_total", "counter", "Code-reveal / rule penalties"),
            ("tokens_total", "tokens_total", "counter", "Estimated tokens used"),
            ("rate_limited", "rate_limited_total", "counter", "Rate-limit rejections"),
            ("llm_errors", "llm_errors_total", "counter", "LLM call failures"),
            ("llm_rate_limited", "llm_rate_limited_total", "counter", "LLM provider 429 after retry/fallback"),
            ("conversations", "conversations", "gauge", "Active in-memory conversations"),
            ("cache_size", "cache_size", "gauge", "Exact-match cache entries"),
        )

        lines: list[str] = []
        for key, metric_suffix, metric_type, help_text in definitions:
            if key in snap:
                metric_name = f"{METRIC_PREFIX}_{metric_suffix}"
                lines.append(f"# HELP {metric_name} {help_text}")
                lines.append(f"# TYPE {metric_name} {metric_type}")
                lines.append(f"{metric_name} {snap[key]}")

        return "\n".join(lines) + "\n"


# Globalny singleton telemetryczny
metrics = MetricsCollector()