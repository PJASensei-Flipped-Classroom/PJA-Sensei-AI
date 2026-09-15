from __future__ import annotations

from collections import OrderedDict
import copy
import hashlib
from threading import Lock
import time
from typing import Any, NamedTuple

from app.core.config import CACHE_MAX_ENTRIES, CACHE_TTL_SECONDS


class _CacheEntry(NamedTuple):
    timestamp: float
    data: dict[str, Any]


def _clone_dict(data: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return copy.deepcopy(data)
    except (TypeError, AttributeError, RecursionError):
        return None


def _build_cache_key(
    conversation_id: str,
    question: str,
    error_logs: str | None,
    current_code: str,
) -> str:
    raw_payload = "\n".join([
        conversation_id,
        question.strip(),
        (error_logs or "").strip(),
        (current_code or "").strip(),
    ])
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


class ExactMatchCache:
    """Wątkowo-bezpieczny cache in-memory z polityką LRU oraz wygasaniem TTL."""

    def __init__(
        self,
        max_entries: int = CACHE_MAX_ENTRIES,
        ttl_seconds: int = CACHE_TTL_SECONDS,
    ):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()

    def get_cached_response(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
    ) -> dict[str, Any] | None:
        key = _build_cache_key(conversation_id, question, error_logs, current_code)

        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            # Sprawdzenie wygaśnięcia wpisu (TTL)
            if (time.monotonic() - entry.timestamp) > self.ttl_seconds:
                del self._store[key]
                return None

            # Przesunięcie na koniec kolejki LRU
            self._store.move_to_end(key)

            cloned_data = _clone_dict(entry.data)
            if cloned_data is None:
                del self._store[key]
                return None

        cloned_data["is_cached"] = True
        return cloned_data

    def save_to_cache(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
        response_data: dict[str, Any],
    ) -> None:
        cloned_payload = _clone_dict(response_data)
        if cloned_payload is None:
            return

        key = _build_cache_key(conversation_id, question, error_logs, current_code)

        with self._lock:
            # Eksmisja najstarszego elementu (LRU), jeśli osiągnięto limit pojemności
            if key not in self._store and len(self._store) >= self.max_entries:
                self._store.popitem(last=False)

            self._store[key] = _CacheEntry(
                timestamp=time.monotonic(),
                data=cloned_payload,
            )
            self._store.move_to_end(key)

    def _evict_expired_entries(self) -> None:
        cutoff_time = time.monotonic() - self.ttl_seconds
        expired_keys = [
            k for k, entry in self._store.items() if entry.timestamp < cutoff_time
        ]
        for k in expired_keys:
            del self._store[k]

    @property
    def size(self) -> int:
        with self._lock:
            self._evict_expired_entries()
            return len(self._store)