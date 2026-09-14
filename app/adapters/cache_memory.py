"""In-memory exact-match response cache (LRU + TTL) implementing CachePort."""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from copy import deepcopy
from typing import Any

from app.core.config import CACHE_MAX_ENTRIES, CACHE_TTL_SECONDS


class ExactMatchCache:
    """Wątkowo-bezpieczny cache LRU w pamięci z obsługą wygasania TTL."""

    def __init__(
        self,
        max_entries: int = CACHE_MAX_ENTRIES,
        ttl_seconds: int = CACHE_TTL_SECONDS,
    ) -> None:
        self._cache: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()

    def _generate_key(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
    ) -> str:
        # Serializacja JSON eliminuje ryzyko przypadkowego łączenia separatorów
        payload = [
            conversation_id,
            question.strip(),
            (error_logs or "").strip(),
            (current_code or "").strip(),
        ]
        raw = json.dumps(payload, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_cached_response(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
    ) -> dict[str, Any] | None:
        """Zwraca głęboką kopię odpowiedzi lub None przy braku / wygaśnięciu wpisu."""
        key = self._generate_key(conversation_id, question, error_logs, current_code)

        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None

            ts, data = entry
            if time.monotonic() - ts > self.ttl_seconds:
                del self._cache[key]
                return None

            self._cache.move_to_end(key)
            result = deepcopy(data)

        # Flaga ustawiona na True dla konsumenta
        result["is_cached"] = True
        return result

    def save_to_cache(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
        response_data: dict[str, Any],
    ) -> None:
        """Zapisuje odpowiedź pod kluczem SHA-256; przy przepełnieniu wyrzuca najstarszy wpis."""
        key = self._generate_key(conversation_id, question, error_logs, current_code)
        payload = deepcopy(response_data)

        with self._lock:
            # Jeśli nadpisujemy istniejący klucz, nie wyrzucamy innego z powodu limitu
            if key not in self._cache and len(self._cache) >= self.max_entries:
                self._cache.popitem(last=False)

            self._cache[key] = (time.monotonic(), payload)
            self._cache.move_to_end(key)

    @property
    def size(self) -> int:
        """Liczba aktywnych wpisów po usunięciu wygasłych (lazy TTL sweep)."""
        with self._lock:
            now = time.monotonic()
            expired = [k for k, (ts, _) in self._cache.items() if now - ts > self.ttl_seconds]
            for k in expired:
                del self._cache[k]
            return len(self._cache)