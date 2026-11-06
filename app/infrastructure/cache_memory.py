import time
from collections import OrderedDict
from typing import Optional, Tuple
from app.domain.ports import CachePort, LlmResult

class InMemoryLruCache(CachePort):
    def __init__(self, max_size: int =128, ttl_seconds: int = 3600):
        self.max_size = max(1, max_size)
        self.ttl_seconds = max(1, ttl_seconds)
        self._store: "OrderedDict[str, Tuple[float, LlmResult]]" = OrderedDict()

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired_keys = [
            key for key, (expires_at, _) in self._store.items() if now >= expires_at
        ]
        for key in expired_keys:
            self._store.pop(key, None)

    def get(self, key: str) -> Optional[LlmResult]:
        self._purge_expired()
        if key not in self._store:
            return None

        expires_at, result = self._store.pop(key)
        self._store[key] = (expires_at, result)

        cached_debug = dict(result.debug_info or {})
        cached_debug["cache_hit"] = True
        return LlmResult(
            raw_content=result.raw_content,
            tokens_used=result.tokens_used,
            model=result.model,
            debug_info=cached_debug,
        )
    def set(self, key: str, value: LlmResult) -> None:
        self._purge_expired()
        if key in self._store:
            self._store.pop(key)
        elif len(self._store) >= self.max_size:
            self._store.popitem(last=False)

        expires_at = time.monotonic() + self.ttl_seconds
        self._store[key] = (expires_at, value)
    def size(self) -> int:
        self._purge_expired()
        return len(self._store)
    def clear(self) -> None:
        self._store.clear()