import hashlib
import time
from collections import OrderedDict
from typing import Any

from app.core.config import CACHE_MAX_ENTRIES, CACHE_TTL_SECONDS


class ExactMatchCache:
    def __init__(
        self,
        max_entries: int = CACHE_MAX_ENTRIES,
        ttl_seconds: int = CACHE_TTL_SECONDS,
    ):
        self._cache: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds

    def _generate_key(
        self, conversation_id: str, question: str, error_logs: str | None, current_code: str
    ) -> str:
        raw = (
            f"{conversation_id}_{question.strip()}_"
            f"{(error_logs or '').strip()}_{(current_code or '').strip()}"
        )
        return hashlib.md5(raw.encode()).hexdigest()

    def get_cached_response(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
    ) -> dict[str, Any] | None:
        key = self._generate_key(conversation_id, question, error_logs, current_code)
        entry = self._cache.get(key)
        if not entry:
            return None

        ts, data = entry
        if time.monotonic() - ts > self.ttl_seconds:
            del self._cache[key]
            return None

        self._cache.move_to_end(key)
        # Copy so callers cannot mutate the stored entry
        return dict(data)

    def save_to_cache(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
        response_data: dict,
    ) -> None:
        key = self._generate_key(conversation_id, question, error_logs, current_code)

        if len(self._cache) >= self.max_entries:
            self._cache.popitem(last=False)

        payload = dict(response_data)
        payload["is_cached"] = False
        self._cache[key] = (time.monotonic(), payload)
        self._cache.move_to_end(key)

    @property
    def size(self) -> int:
        now = time.monotonic()
        expired = [k for k, (ts, _) in self._cache.items() if now - ts > self.ttl_seconds]
        for k in expired:
            del self._cache[k]
        return len(self._cache)