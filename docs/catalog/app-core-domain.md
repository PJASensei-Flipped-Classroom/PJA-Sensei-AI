# app/ — core i domain

Opisy linia-po-linii (język: polski). Puste linie pominięte w wypunktowaniu, ale nie zmieniają numeracji `L`.

<a id="app-init-py"></a>
## `app/__init__.py`
Znacznik pakietu głównego aplikacji (pusty).

Liczba linii: **0** (pusty plik).

### Opis linia-po-linii

- *(brak linii — plik pusty / znacznik pakietu)*

<a id="app-main-py"></a>
## `app/main.py`
Fabryka FastAPI (`create_app`), lifespan kontenera, CORS, routery chronione i publiczne; eksport `app`.

Liczba linii: **79**.

### Opis linia-po-linii

- **L1:** Docstring: FastAPI application factory.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L6:** Importy — L5: `import logging`; L6: `from contextlib import asynccontextmanager`.
- **L8–L9:** Importy — L8: `from fastapi import APIRouter, Depends, FastAPI`; L9: `from fastapi.middleware.cors import CORSMiddleware`.
- **L11–L24:** Importy — L11: `from app.api.deps import enforce_rate_limit, init_container`; L12: `from app.api.errors import register_exception_handlers`; L13: `from app.api.middleware import RequestIdMiddleware`; L14: `from app.api.routers import (`; L15: `analytics,`; L16: `config_validate,`; L17: `conversations,`; L18: `health,`; L19: `messages,`; L20: `prelab,`; L21: `)`; L22: `from app.application.container import AppContainer`; L23: `from app.core.auth import require_auth`; L24: `from app.core.config import CORS_ORIGINS`.
- **L26:** Przypisanie `logger` ← `logging.getLogger(__name__)`.
- **L29:** Definicja funkcji/metody `create_app`, zwraca `FastAPI`.
- **L30:** (w `create_app`) Dekorator `@asynccontextmanager` (np. route FastAPI, fixture, dataclass).
- **L31:** Definicja asynchronicznej funkcji/metody `lifespan`.
- **L32:** (w `create_app`) Przypisanie `app.state.container` ← `container or init_container()`.
- **L33:** (w `create_app`) Log: `logger.info("Application container initialized.")`.
- **L34:** (w `create_app`) Blok `try` — chroniony kod, potem except/finally.
- **L35:** (w `create_app`) Yield bez wartości.
- **L36:** (w `create_app`) Blok `finally` — zawsze na wyjściu z `try`.
- **L37:** (w `create_app`) Przypisanie `shutdown` ← `getattr(app.state.container, "shutdown", None)`.
- **L38:** (w `create_app`) Warunek `if` — gdy `callable(shutdown)`.
- **L39:** (w `create_app`) Oczekuje na coroutine: `shutdown()`.
- **L41–L44:** (w `create_app`) Wyrażenie wieloliniowe — L41: Przypisanie `app` ← `FastAPI(`. | L42: Przypisanie `title` ← `"PJA-Sensei AI Microservice",`. | L43: Przypisanie `lifespan` ← `lifespan,`. | L44: Zamknięcie wyrażenia (`)`).
- **L46:** (w `create_app`) Wykonuje: `app.add_middleware(RequestIdMiddleware)`.
- **L47–L54:** (w `create_app`) Wyrażenie wieloliniowe — L47: Wykonuje: `app.add_middleware(`. | L48: Element listy/argumentów: `CORSMiddleware,`. | L49: Przypisanie `allow_origins` ← `CORS_ORIGINS,`. | L50: Przypisanie `allow_credentials` ← `True,`. | L51: Przypisanie `allow_methods` ← `["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],`. | L52: Przypisanie `allow_headers` ← `["Authorization", "Content-Type", "X-Request-Id"],`. | L53: Przypisanie `expose_headers` ← `["X-Message-Id", "X-Request-Id"],`. | L54: Zamknięcie wyrażenia (`)`).
- **L56:** (w `create_app`) Wykonuje: `register_exception_handlers(app)`.
- **L58:** (w `create_app`) Wykonuje: `app.include_router(health.router)`.
- **L60–L62:** (w `create_app`) Wyrażenie wieloliniowe — L60: Przypisanie `protected` ← `APIRouter(`. | L61: Przypisanie `dependencies` ← `[Depends(require_auth), Depends(enforce_rate_limit)]`. | L62: Zamknięcie wyrażenia (`)`).
- **L64–L70:** (w `create_app`) Wyrażenie wieloliniowe — L64: Przypisanie `protected_routers` ← `[`. | L65: Element listy/argumentów: `config_validate.router,`. | L66: Element listy/argumentów: `analytics.router,`. | L67: Element listy/argumentów: `conversations.router,`. | L68: Element listy/argumentów: `messages.router,`. | L69: Element listy/argumentów: `prelab.router,`. | L70: Zamknięcie wyrażenia (`]`).
- **L71:** (w `create_app`) Pętla `for` po `router in protected_routers`.
- **L72:** (w `create_app`) Wykonuje: `protected.include_router(router)`.
- **L74:** (w `create_app`) Wykonuje: `app.include_router(protected)`.
- **L76:** (w `create_app`) Zwraca: `app`.
- **L79:** Przypisanie `app` ← `create_app()`.

<a id="app-core-init-py"></a>
## `app/core/__init__.py`
Pakiet infrastruktury: ustawienia, auth, metryki, rate limiting.

Liczba linii: **1**.

### Opis linia-po-linii

- **L1:** Docstring: Core infrastructure: settings, auth, metrics, rate limiting.

<a id="app-core-config-py"></a>
## `app/core/config.py`
Ustawienia pydantic-settings oraz eksport stałych konfiguracyjnych używanych w całym module.

Liczba linii: **78**.

### Opis linia-po-linii

- **L1:** Docstring: Application settings (pydantic-settings).
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L6:** Importy — L5: `from datetime import timedelta`; L6: `from functools import lru_cache`.
- **L8–L8:** Importy — L8: `from pydantic_settings import BaseSettings, SettingsConfigDict`.
- **L11:** Definicja klasy `Settings` dziedziczy/parametryzuje: `(BaseSettings)`.
- **L12–L17:** (w `Settings`) Wyrażenie wieloliniowe — L12: Przypisanie `model_config` ← `SettingsConfigDict(`. | L13: Przypisanie `env_file` ← `".env",`. | L14: Przypisanie `env_file_encoding` ← `"utf-8",`. | L15: Przypisanie `extra` ← `"ignore",`. | L16: Przypisanie `case_sensitive` ← `False,`. | L17: Zamknięcie wyrażenia (`)`).
- **L19:** (w `Settings`) Przypisanie `openrouter_api_key: str | None` ← `None`.
- **L20:** (w `Settings`) Przypisanie `openrouter_base_url: str` ← `"https://openrouter.ai/api/v1"`.
- **L21:** (w `Settings`) Przypisanie `main_model: str` ← `"meta-llama/llama-3.3-70b-instruct"`.
- **L22:** (w `Settings`) Przypisanie `security_model: str` ← `"meta-llama/llama-3.1-8b-instruct"`.
- **L24:** (w `Settings`) Przypisanie `telemetry_url: str` ← `"http://localhost:8080/api/ai/telemetry"`.
- **L25:** (w `Settings`) Przypisanie `summary_webhook_url: str | None` ← `None`.
- **L27–L30:** (w `Settings`) Wyrażenie wieloliniowe — L27: Przypisanie `cors_origins: str` ← `(`. | L28: Wykonuje: `"http://localhost:8000,http://127.0.0.1:8000,"`. | L29: Wykonuje: `"http://localhost:5500,http://127.0.0.1:5500,null"`. | L30: Zamknięcie wyrażenia (`)`).
- **L32:** (w `Settings`) Przypisanie `ai_auth_enabled: bool` ← `False`.
- **L33:** (w `Settings`) Przypisanie `ai_jwt_secret: str` ← `""`.
- **L34:** (w `Settings`) Przypisanie `ai_jwt_algorithm: str` ← `"HS256"`.
- **L36:** (w `Settings`) Przypisanie `rate_limit_per_minute: int` ← `30`.
- **L37:** (w `Settings`) Przypisanie `cache_ttl_seconds: int` ← `30 * 60`.
- **L38:** (w `Settings`) Przypisanie `cache_max_entries: int` ← `500`.
- **L39:** (w `Settings`) Przypisanie `conversation_ttl_seconds: int` ← `2 * 3600`.
- **L40:** (w `Settings`) Przypisanie `max_conversations: int` ← `200`.
- **L41:** (w `Settings`) Przypisanie `security_fail_closed: bool` ← `False`.
- **L43:** (w `Settings`) Dekorator `@property` (np. route FastAPI, fixture, dataclass).
- **L44:** Definicja funkcji/metody `cors_origin_list`, zwraca `list[str]`.
- **L45:** (w `Settings`) Zwraca: `[origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]`.
- **L47:** (w `Settings`) Dekorator `@property` (np. route FastAPI, fixture, dataclass).
- **L48:** Definicja funkcji/metody `conversation_ttl`, zwraca `timedelta`.
- **L49:** (w `Settings`) Zwraca: `timedelta(seconds=self.conversation_ttl_seconds)`.
- **L51:** (w `Settings`) Dekorator `@property` (np. route FastAPI, fixture, dataclass).
- **L52:** Definicja funkcji/metody `resolved_summary_webhook_url`, zwraca `str`.
- **L53:** (w `Settings`) Zwraca: `self.summary_webhook_url or self.telemetry_url`.
- **L56:** Dekorator `@lru_cache` (np. route FastAPI, fixture, dataclass).
- **L57:** Definicja funkcji/metody `get_settings`, zwraca `Settings`.
- **L58:** (w `get_settings`) Zwraca: `Settings()`.
- **L61:** Przypisanie `_settings` ← `get_settings()`.
- **L63:** Przypisanie `OPENROUTER_API_KEY` ← `_settings.openrouter_api_key`.
- **L64:** Przypisanie `OPENROUTER_BASE_URL` ← `_settings.openrouter_base_url`.
- **L65:** Przypisanie `MAIN_MODEL` ← `_settings.main_model`.
- **L66:** Przypisanie `SECURITY_MODEL` ← `_settings.security_model`.
- **L67:** Przypisanie `TELEMETRY_URL` ← `_settings.telemetry_url`.
- **L68:** Przypisanie `SUMMARY_WEBHOOK_URL` ← `_settings.resolved_summary_webhook_url`.
- **L69:** Przypisanie `CORS_ORIGINS` ← `_settings.cors_origin_list`.
- **L70:** Przypisanie `AI_AUTH_ENABLED` ← `_settings.ai_auth_enabled`.
- **L71:** Przypisanie `AI_JWT_SECRET` ← `_settings.ai_jwt_secret`.
- **L72:** Przypisanie `AI_JWT_ALGORITHM` ← `_settings.ai_jwt_algorithm`.
- **L73:** Przypisanie `RATE_LIMIT_PER_MINUTE` ← `_settings.rate_limit_per_minute`.
- **L74:** Przypisanie `CACHE_TTL_SECONDS` ← `_settings.cache_ttl_seconds`.
- **L75:** Przypisanie `CACHE_MAX_ENTRIES` ← `_settings.cache_max_entries`.
- **L76:** Przypisanie `CONVERSATION_TTL` ← `_settings.conversation_ttl`.
- **L77:** Przypisanie `MAX_CONVERSATIONS` ← `_settings.max_conversations`.
- **L78:** Przypisanie `SECURITY_FAIL_CLOSED` ← `_settings.security_fail_closed`.

<a id="app-core-auth-py"></a>
## `app/core/auth.py`
Zależność FastAPI walidująca Bearer JWT gdy `AI_AUTH_ENABLED`.

Liczba linii: **55**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `import logging`.
- **L3–L4:** Importy — L3: `from fastapi import Depends, HTTPException, status`; L4: `from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer`.
- **L6–L6:** Importy — L6: `from app.core.config import AI_AUTH_ENABLED, AI_JWT_ALGORITHM, AI_JWT_SECRET`.
- **L8:** Przypisanie `logger` ← `logging.getLogger(__name__)`.
- **L9:** Przypisanie `_bearer` ← `HTTPBearer(auto_error=False)`.
- **L12–L14:** (w `require_auth`) Wyrażenie wieloliniowe — L12: Definicja funkcji/metody `?`. | L13: Przypisanie `credentials: HTTPAuthorizationCredentials | None` ← `Depends(_bearer),`. | L14: Wykonuje: `) -> str | None:`.
- **L15:** Docstring: Validate Bearer JWT when AI_AUTH_ENABLED. Returns subject or None if auth off.
- **L16:** (w `require_auth`) Warunek `if` — gdy `not AI_AUTH_ENABLED`.
- **L17:** (w `require_auth`) Zwraca: `None`.
- **L19:** (w `require_auth`) Warunek `if` — gdy `not AI_JWT_SECRET`.
- **L20:** (w `require_auth`) Log: `logger.error("AI_AUTH_ENABLED but AI_JWT_SECRET is empty")`.
- **L21–L24:** (w `require_auth`) Wyrażenie wieloliniowe — L21: Rzuca wyjątek: `HTTPException(`. | L22: Przypisanie `status_code` ← `status.HTTP_500_INTERNAL_SERVER_ERROR,`. | L23: Przypisanie `detail` ← `"Auth misconfigured",`. | L24: Zamknięcie wyrażenia (`)`).
- **L26:** (w `require_auth`) Warunek `if` — gdy `credentials is None or credentials.scheme.lower() != "bearer"`.
- **L27–L31:** (w `require_auth`) Wyrażenie wieloliniowe — L27: Rzuca wyjątek: `HTTPException(`. | L28: Przypisanie `status_code` ← `status.HTTP_401_UNAUTHORIZED,`. | L29: Przypisanie `detail` ← `"Missing Bearer token",`. | L30: Przypisanie `headers` ← `{"WWW-Authenticate": "Bearer"},`. | L31: Zamknięcie wyrażenia (`)`).
- **L33:** (w `require_auth`) Blok `try` — chroniony kod, potem except/finally.
- **L34–L34:** Importy — L34: `import jwt`.
- **L36–L40:** (w `require_auth`) Wyrażenie wieloliniowe — L36: Przypisanie `payload` ← `jwt.decode(`. | L37: Element listy/argumentów: `credentials.credentials,`. | L38: Element listy/argumentów: `AI_JWT_SECRET,`. | L39: Przypisanie `algorithms` ← `[AI_JWT_ALGORITHM],`. | L40: Zamknięcie wyrażenia (`)`).
- **L41:** (w `require_auth`) Przechwytuje wyjątek `Exception as exc`.
- **L42:** (w `require_auth`) Log: `logger.warning("JWT validation failed: %s", exc)`.
- **L43–L47:** (w `require_auth`) Wyrażenie wieloliniowe — L43: Rzuca wyjątek: `HTTPException(`. | L44: Przypisanie `status_code` ← `status.HTTP_401_UNAUTHORIZED,`. | L45: Przypisanie `detail` ← `"Invalid token",`. | L46: Przypisanie `headers` ← `{"WWW-Authenticate": "Bearer"},`. | L47: Wykonuje: `) from exc`.
- **L49:** (w `require_auth`) Przypisanie `sub` ← `payload.get("sub")`.
- **L50:** (w `require_auth`) Warunek `if` — gdy `not sub`.
- **L51–L54:** (w `require_auth`) Wyrażenie wieloliniowe — L51: Rzuca wyjątek: `HTTPException(`. | L52: Przypisanie `status_code` ← `status.HTTP_401_UNAUTHORIZED,`. | L53: Przypisanie `detail` ← `"Token missing sub claim",`. | L54: Zamknięcie wyrażenia (`)`).
- **L55:** (w `require_auth`) Zwraca: `str(sub)`.

<a id="app-core-metrics-py"></a>
## `app/core/metrics.py`
Wewnętrzny kolektor metryk (liczniki + eksport Prometheus text).

Liczba linii: **81**.

### Opis linia-po-linii

- **L1:** Docstring: In-process metrics for the AI microservice.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L7:** Importy — L5: `import threading`; L6: `from dataclasses import dataclass, field`; L7: `from typing import Any`.
- **L9:** Przypisanie `METRIC_PREFIX` ← `"pja_sensei"`.
- **L12:** Dekorator `@dataclass` (np. route FastAPI, fixture, dataclass).
- **L13:** Definicja klasy `MetricsCollector`.
- **L14:** (w `MetricsCollector`) Przypisanie `requests_total: int` ← `0`.
- **L15:** (w `MetricsCollector`) Przypisanie `messages_total: int` ← `0`.
- **L16:** (w `MetricsCollector`) Przypisanie `cache_hits: int` ← `0`.
- **L17:** (w `MetricsCollector`) Przypisanie `cache_misses: int` ← `0`.
- **L18:** (w `MetricsCollector`) Przypisanie `penalties_total: int` ← `0`.
- **L19:** (w `MetricsCollector`) Przypisanie `tokens_total: int` ← `0`.
- **L20:** (w `MetricsCollector`) Przypisanie `rate_limited: int` ← `0`.
- **L21:** (w `MetricsCollector`) Przypisanie `llm_errors: int` ← `0`.
- **L22:** (w `MetricsCollector`) Przypisanie `_lock: threading.Lock` ← `field(default_factory=threading.Lock, repr=False)`.
- **L24:** Definicja funkcji/metody `inc`, zwraca `None`.
- **L25:** (w `MetricsCollector`) Context manager: `with self._lock:`.
- **L26:** (w `MetricsCollector`) Przypisanie `current` ← `getattr(self, name, None)`.
- **L27:** (w `MetricsCollector`) Warunek `if` — gdy `isinstance(current, (int, float))`.
- **L28:** (w `MetricsCollector`) Wykonuje: `setattr(self, name, current + amount)`.
- **L30:** Definicja funkcji/metody `snapshot`, zwraca `dict[str, Any]`.
- **L31:** (w `MetricsCollector`) Context manager: `with self._lock:`.
- **L32:** (w `MetricsCollector`) Przypisanie `hits` ← `self.cache_hits`.
- **L33:** (w `MetricsCollector`) Przypisanie `misses` ← `self.cache_misses`.
- **L34:** (w `MetricsCollector`) Przypisanie `denom` ← `hits + misses`.
- **L35:** (w `MetricsCollector`) Przypisanie `msg_total` ← `self.messages_total`.
- **L37–L48:** (w `MetricsCollector`) Wyrażenie wieloliniowe — L37: Zwraca: `{`. | L38: Element listy/argumentów: `"requests_total": self.requests_total,`. | L39: Element listy/argumentów: `"messages_total": msg_total,`. | L40: Element listy/argumentów: `"cache_hits": hits,`. | L41: Element listy/argumentów: `"cache_misses": misses,`. | L42: Element listy/argumentów: `"cache_hit_rate": round(hits / denom, 3) if denom else 0.0,`. | L43: Element listy/argumentów: `"penalties_total": self.penalties_total,`. | L44: Element listy/argumentów: `"tokens_total": self.tokens_total,`. | L45: Element listy/argumentów: `"avg_tokens_per_message": round(self.tokens_total / msg_total, 1) if msg_total else 0.0,`. | L46: Element listy/argumentów: `"rate_limited": self.rate_limited,`. | L47: Element listy/argumentów: `"llm_errors": self.llm_errors,`. | L48: Zamknięcie wyrażenia (`}`).
- **L50:** Definicja funkcji/metody `prometheus_text`, zwraca `str`.
- **L51:** (w `MetricsCollector`) Przypisanie `snap` ← `self.snapshot()`.
- **L52:** (w `MetricsCollector`) Warunek `if` — gdy `extra`.
- **L53:** (w `MetricsCollector`) Wykonuje: `snap.update(extra)`.
- **L55–L66:** (w `MetricsCollector`) Wyrażenie wieloliniowe — L55: Przypisanie `definitions` ← `[`. | L56: Element listy/argumentów: `("requests_total", "requests_total", "counter", "Total HTTP-tracked requests"),`. | L57: Element listy/argumentów: `("messages_total", "messages_total", "counter", "Total chat messages processed"),`. | L58: Element listy/argumentów: `("cache_hits", "cache_hits_total", "counter", "Exact-match cache hits"),`. | L59: Element listy/argumentów: `("cache_misses", "cache_misses_total", "counter", "Exact-match cache misses"),`. | L60: Element listy/argumentów: `("penalties_total", "penalties_total", "counter", "Code-reveal / rule penalties"),`. | L61: Element listy/argumentów: `("tokens_total", "tokens_total", "counter", "Estimated tokens used"),`. | L62: Element listy/argumentów: `("rate_limited", "rate_limited_total", "counter", "Rate-limit rejections"),`. | L63: Element listy/argumentów: `("llm_errors", "llm_errors_total", "counter", "LLM call failures"),`. | L64: Element listy/argumentów: `("conversations", "conversations", "gauge", "Active in-memory conversations"),`. | L65: Element listy/argumentów: `("cache_size", "cache_size", "gauge", "Exact-match cache entries"),`. | L66: Zamknięcie wyrażenia (`]`).
- **L68:** (w `MetricsCollector`) Przypisanie `lines: list[str]` ← `[]`.
- **L69:** (w `MetricsCollector`) Pętla `for` po `key, metric_suffix, metric_type, help_text in definitions`.
- **L70:** (w `MetricsCollector`) Warunek `if` — gdy `key in snap`.
- **L71:** (w `MetricsCollector`) Przypisanie `metric_name` ← `f"{METRIC_PREFIX}_{metric_suffix}"`.
- **L72–L76:** (w `MetricsCollector`) Wyrażenie wieloliniowe — L72: Wykonuje: `lines.extend([`. | L73: Element listy/argumentów: `f"# HELP {metric_name} {help_text}",`. | L74: Element listy/argumentów: `f"# TYPE {metric_name} {metric_type}",`. | L75: Element listy/argumentów: `f"{metric_name} {snap[key]}",`. | L76: Wykonuje: `])`.
- **L78:** (w `MetricsCollector`) Zwraca: `"\n".join(lines) + "\n"`.
- **L81:** Przypisanie `metrics` ← `MetricsCollector()`.

<a id="app-core-rate-limit-py"></a>
## `app/core/rate_limit.py`
Sliding-window rate limiter per IP/konwersacja oraz helper klucza klienta.

Liczba linii: **71**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L6:** Importy — L3: `import math`; L4: `import threading`; L5: `import time`; L6: `from collections import deque`.
- **L8–L8:** Importy — L8: `from fastapi import HTTPException, Request, status`.
- **L10–L11:** Importy — L10: `from app.core.config import RATE_LIMIT_PER_MINUTE`; L11: `from app.core.metrics import metrics`.
- **L13:** Przypisanie `WINDOW_SECONDS` ← `60.0`.
- **L16:** Definicja klasy `RateLimiter`.
- **L17:** Definicja funkcji/metody `__init__`.
- **L18:** (w `RateLimiter`) Przypisanie `self.limit` ← `limit_per_minute`.
- **L19:** (w `RateLimiter`) Przypisanie `self._hits: dict[str, deque[float]]` ← `{}`.
- **L20:** (w `RateLimiter`) Przypisanie `self._lock` ← `threading.Lock()`.
- **L22:** Definicja funkcji/metody `check`, zwraca `None`.
- **L23:** (w `RateLimiter`) Przypisanie `now` ← `time.monotonic()`.
- **L25:** (w `RateLimiter`) Context manager: `with self._lock:`.
- **L26:** (w `RateLimiter`) Przypisanie `window` ← `self._hits.get(key)`.
- **L27:** (w `RateLimiter`) Warunek `if` — gdy `window is None`.
- **L28:** (w `RateLimiter`) Przypisanie `window` ← `deque()`.
- **L29:** (w `RateLimiter`) Przypisanie `self._hits[key]` ← `window`.
- **L31:** (w `RateLimiter`) Pętla `while` dopóki `window and (now - window[0]) > WINDOW_SECONDS`.
- **L32:** (w `RateLimiter`) Wykonuje: `window.popleft()`.
- **L34:** (w `RateLimiter`) Warunek `if` — gdy `len(window) >= self.limit`.
- **L35:** (w `RateLimiter`) Wykonuje: `metrics.inc("rate_limited")`.
- **L36:** (w `RateLimiter`) Przypisanie `retry_after` ← `max(1, math.ceil(WINDOW_SECONDS - (now - window[0])))`.
- **L37–L41:** (w `RateLimiter`) Wyrażenie wieloliniowe — L37: Rzuca wyjątek: `HTTPException(`. | L38: Przypisanie `status_code` ← `status.HTTP_429_TOO_MANY_REQUESTS,`. | L39: Przypisanie `detail` ← `"Rate limit exceeded",`. | L40: Przypisanie `headers` ← `{"Retry-After": str(retry_after)},`. | L41: Zamknięcie wyrażenia (`)`).
- **L43:** (w `RateLimiter`) Wykonuje: `window.append(now)`.
- **L45:** (w `RateLimiter`) Warunek `if` — gdy `len(self._hits) > 10_000`.
- **L46:** (w `RateLimiter`) Wykonuje: `self._cleanup_stale_keys(now)`.
- **L48:** Definicja funkcji/metody `_cleanup_stale_keys`, zwraca `None`.
- **L49–L52:** (w `RateLimiter`) Wyrażenie wieloliniowe — L49: Przypisanie `stale_keys` ← `[`. | L50: Wykonuje: `k for k, win in self._hits.items()`. | L51: Warunek `if` — gdy `not win or (now - win[-1]) > WINDOW_SECONDS`. | L52: Zamknięcie wyrażenia (`]`).
- **L53:** (w `RateLimiter`) Pętla `for` po `k in stale_keys`.
- **L54:** (w `RateLimiter`) Wykonuje: `del self._hits[k]`.
- **L57:** Przypisanie `rate_limiter` ← `RateLimiter()`.
- **L60:** Definicja funkcji/metody `client_key`, zwraca `str`.
- **L61:** Docstring: Rate-limit bucket: conversation id if present, else client IP.
- **L62:** (w `client_key`) Warunek `if` — gdy `conversation_id`.
- **L63:** (w `client_key`) Zwraca: `f"conv:{conversation_id}"`.
- **L65:** (w `client_key`) Przypisanie `forwarded` ← `request.headers.get("x-forwarded-for")`.
- **L66:** (w `client_key`) Warunek `if` — gdy `forwarded`.
- **L67:** (w `client_key`) Przypisanie `client_ip` ← `forwarded.split(",")[0].strip()`.
- **L68:** (w `client_key`) Zwraca: `f"ip:{client_ip}"`.
- **L70:** (w `client_key`) Przypisanie `client_ip` ← `request.client.host if request.client else "unknown"`.
- **L71:** (w `client_key`) Zwraca: `f"ip:{client_ip}"`.

<a id="app-domain-init-py"></a>
## `app/domain/__init__.py`
Pakiet modeli domenowych bez zależności HTTP/LLM.

Liczba linii: **1**.

### Opis linia-po-linii

- **L1:** Docstring: Domain models and exceptions (no FastAPI / OpenAI imports).

<a id="app-domain-exceptions-py"></a>
## `app/domain/exceptions.py`
Wyjątki domenowe mapowane później na odpowiedzi HTTP.

Liczba linii: **19**.

### Opis linia-po-linii

- **L1:** Docstring: Domain exceptions.
- **L4:** Definicja klasy `UnknownConversation` dziedziczy/parametryzuje: `(Exception)`.
- **L5:** (w `UnknownConversation`) Puste ciało (`pass`) — znacznik pakietu lub placeholder.
- **L8:** Definicja klasy `PrelabRequired` dziedziczy/parametryzuje: `(Exception)`.
- **L9:** (w `PrelabRequired`) Puste ciało (`pass`) — znacznik pakietu lub placeholder.
- **L12:** Definicja klasy `TokenBudgetExceeded` dziedziczy/parametryzuje: `(Exception)`.
- **L13:** (w `TokenBudgetExceeded`) Puste ciało (`pass`) — znacznik pakietu lub placeholder.
- **L16:** Definicja klasy `RevealNotAllowed` dziedziczy/parametryzuje: `(Exception)`.
- **L17:** Definicja funkcji/metody `__init__`.
- **L18:** (w `RevealNotAllowed`) Przypisanie `self.detail` ← `detail`.
- **L19:** (w `RevealNotAllowed`) Wykonuje: `super().__init__(detail)`.

<a id="app-domain-sensei-py"></a>
## `app/domain/sensei.py`
Modele Pydantic SenseiConfig, kontekstu kodu IDE i materiałów referencyjnych.

Liczba linii: **98**.

### Opis linia-po-linii

- **L1:** Docstring: Sensei lab configuration and nested domain models.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `from typing import Literal`.
- **L7–L7:** Importy — L7: `from pydantic import BaseModel, Field`.
- **L10:** Definicja klasy `ReferenceMaterial` dziedziczy/parametryzuje: `(BaseModel)`.
- **L11:** (w `ReferenceMaterial`) Przypisanie `type: Literal["doc", "pdf", "video_timestamp", "slide"]` ← `"doc"`.
- **L12:** (w `ReferenceMaterial`) Wykonuje: `title: str`.
- **L13:** (w `ReferenceMaterial`) Wykonuje: `url: str`.
- **L14:** (w `ReferenceMaterial`) Przypisanie `timestamp: str | None` ← `None`.
- **L15:** (w `ReferenceMaterial`) Przypisanie `page: int | None` ← `None`.
- **L18:** Definicja klasy `LearningContext` dziedziczy/parametryzuje: `(BaseModel)`.
- **L19:** (w `LearningContext`) Wykonuje: `goals: list[str]`.
- **L20:** (w `LearningContext`) Wykonuje: `referenceMaterials: list[ReferenceMaterial]`.
- **L23:** Definicja klasy `AgentPersona` dziedziczy/parametryzuje: `(BaseModel)`.
- **L24:** (w `AgentPersona`) Wykonuje: `role: str`.
- **L25:** (w `AgentPersona`) Wykonuje: `tone: str`.
- **L28:** Definicja klasy `AgentBehavior` dziedziczy/parametryzuje: `(BaseModel)`.
- **L29:** (w `AgentBehavior`) Wykonuje: `persona: AgentPersona`.
- **L30:** (w `AgentBehavior`) Przypisanie `codeRevealFallback: str | None` ← `None`.
- **L31:** (w `AgentBehavior`) Wykonuje: `strictRules: list[str]`.
- **L32:** (w `AgentBehavior`) Przypisanie `model: str | None` ← `None`.
- **L33:** (w `AgentBehavior`) Przypisanie `mode: Literal["theory", "debug", "review"]` ← `"debug"`.
- **L36:** Definicja klasy `IdeRestrictions` dziedziczy/parametryzuje: `(BaseModel)`.
- **L37:** (w `IdeRestrictions`) Przypisanie `requireFileContextForChat: bool` ← `False`.
- **L38:** (w `IdeRestrictions`) Przypisanie `disableCopyFromChat: bool` ← `False`.
- **L41:** Definicja klasy `Checkpoint` dziedziczy/parametryzuje: `(BaseModel)`.
- **L42:** (w `Checkpoint`) Wykonuje: `id: str`.
- **L43:** (w `Checkpoint`) Przypisanie `after_goal: str | None` ← `None`.
- **L44:** (w `Checkpoint`) Przypisanie `hint: str | None` ← `None`.
- **L47:** Definicja klasy `PreLabQuestion` dziedziczy/parametryzuje: `(BaseModel)`.
- **L48:** (w `PreLabQuestion`) Wykonuje: `id: str`.
- **L49:** (w `PreLabQuestion`) Wykonuje: `prompt: str`.
- **L50:** (w `PreLabQuestion`) Przypisanie `expected_keywords: list[str]` ← `Field(default_factory=list)`.
- **L53:** Definicja klasy `PreLabConfig` dziedziczy/parametryzuje: `(BaseModel)`.
- **L54:** (w `PreLabConfig`) Przypisanie `enabled: bool` ← `False`.
- **L55:** (w `PreLabConfig`) Przypisanie `questions: list[PreLabQuestion]` ← `Field(default_factory=list)`.
- **L56:** (w `PreLabConfig`) Przypisanie `max_attempts: int | None` ← `None`.
- **L57:** (w `PreLabConfig`) Przypisanie `hint_after_fail: str | None` ← `None`.
- **L60:** Definicja klasy `SenseiConfig` dziedziczy/parametryzuje: `(BaseModel)`.
- **L61:** (w `SenseiConfig`) Wykonuje: `learningContext: LearningContext`.
- **L62:** (w `SenseiConfig`) Wykonuje: `agentBehavior: AgentBehavior`.
- **L63:** (w `SenseiConfig`) Przypisanie `ideRestrictions: IdeRestrictions | None` ← `None`.
- **L64:** (w `SenseiConfig`) Przypisanie `language: Literal["pl", "en"]` ← `"pl"`.
- **L65:** (w `SenseiConfig`) Przypisanie `preLab: PreLabConfig | None` ← `None`.
- **L66:** (w `SenseiConfig`) Przypisanie `evaluationCriteria: list[str]` ← `Field(default_factory=list)`.
- **L67:** (w `SenseiConfig`) Przypisanie `maxTokensPerSession: int | None` ← `None`.
- **L68:** (w `SenseiConfig`) Przypisanie `checkpoints: list[Checkpoint]` ← `Field(default_factory=list)`.
- **L71:** Definicja klasy `CodeSelection` dziedziczy/parametryzuje: `(BaseModel)`.
- **L72:** (w `CodeSelection`) Wykonuje: `start_line: int`.
- **L73:** (w `CodeSelection`) Wykonuje: `end_line: int`.
- **L74:** (w `CodeSelection`) Przypisanie `text: str | None` ← `None`.
- **L77:** Definicja klasy `DiagnosticItem` dziedziczy/parametryzuje: `(BaseModel)`.
- **L78:** (w `DiagnosticItem`) Przypisanie `file: str | None` ← `None`.
- **L79:** (w `DiagnosticItem`) Przypisanie `severity: Literal["error", "warning", "info", "hint"]` ← `"error"`.
- **L80:** (w `DiagnosticItem`) Wykonuje: `message: str`.
- **L81:** (w `DiagnosticItem`) Przypisanie `line: int | None` ← `None`.
- **L82:** (w `DiagnosticItem`) Przypisanie `source: str | None` ← `None`.
- **L85:** Definicja klasy `OpenFile` dziedziczy/parametryzuje: `(BaseModel)`.
- **L86:** (w `OpenFile`) Wykonuje: `path: str`.
- **L87:** (w `OpenFile`) Wykonuje: `content: str`.
- **L88:** (w `OpenFile`) Przypisanie `language: str | None` ← `None`.
- **L91:** Definicja klasy `CodeContext` dziedziczy/parametryzuje: `(BaseModel)`.
- **L92:** (w `CodeContext`) Wykonuje: `current_file_name: str`.
- **L93:** (w `CodeContext`) Wykonuje: `current_code: str`.
- **L94:** (w `CodeContext`) Przypisanie `error_logs: str | None` ← `None`.
- **L95:** (w `CodeContext`) Przypisanie `workspace_root: str | None` ← `None`.
- **L96:** (w `CodeContext`) Przypisanie `selection: CodeSelection | None` ← `None`.
- **L97:** (w `CodeContext`) Przypisanie `diagnostics: list[DiagnosticItem]` ← `Field(default_factory=list)`.
- **L98:** (w `CodeContext`) Przypisanie `open_files: list[OpenFile]` ← `Field(default_factory=list)`.

<a id="app-domain-conversation-py"></a>
## `app/domain/conversation.py`
Agregat Conversation w pamięci oraz helpery frustracji / scoringu.

Liczba linii: **97**.

### Opis linia-po-linii

- **L1:** Docstring: In-memory conversation aggregate.
- **L3–L5:** Importy — L3: `from dataclasses import dataclass, field`; L4: `from datetime import datetime, timezone`; L5: `from typing import Any`.
- **L7–L7:** Importy — L7: `from app.domain.sensei import SenseiConfig`.
- **L9:** Przypisanie `FRUSTRATION_THRESHOLD` ← `4`.
- **L10:** Przypisanie `FRUSTRATION_STREAK` ← `3`.
- **L13–L15:** (w `consecutive_low_scores`) Wyrażenie wieloliniowe — L13: Definicja funkcji/metody `?`. | L14: Przypisanie `scores: list[int], threshold: int` ← `FRUSTRATION_THRESHOLD`. | L15: Wykonuje: `) -> int:`.
- **L16:** (w `consecutive_low_scores`) Przypisanie `count` ← `0`.
- **L17:** (w `consecutive_low_scores`) Pętla `for` po `score in reversed(scores)`.
- **L18:** (w `consecutive_low_scores`) Warunek `if` — gdy `score <= threshold`.
- **L19:** (w `consecutive_low_scores`) Przypisanie `count +` ← `1`.
- **L20:** (w `consecutive_low_scores`) Gałąź `else` (pozostałe przypadki).
- **L21:** (w `consecutive_low_scores`) Przerywa pętlę (`break`).
- **L22:** (w `consecutive_low_scores`) Zwraca: `count`.
- **L25:** Definicja funkcji/metody `is_frustrated`, zwraca `bool`.
- **L26:** (w `is_frustrated`) Zwraca: `consecutive_low_scores(scores) >= FRUSTRATION_STREAK`.
- **L29:** Definicja funkcji/metody `recent_avg_score`, zwraca `float`.
- **L30:** (w `recent_avg_score`) Warunek `if` — gdy `not scores`.
- **L31:** (w `recent_avg_score`) Zwraca: `0.0`.
- **L32:** (w `recent_avg_score`) Przypisanie `recent` ← `scores[-3:]`.
- **L33:** (w `recent_avg_score`) Zwraca: `sum(recent) / len(recent)`.
- **L36–L40:** (w `consecutive_low_enough`) Wyrażenie wieloliniowe — L36: Definicja funkcji/metody `?`. | L37: Element listy/argumentów: `scores: list[int],`. | L38: Przypisanie `n: int` ← `FRUSTRATION_STREAK,`. | L39: Przypisanie `threshold: int` ← `FRUSTRATION_THRESHOLD,`. | L40: Wykonuje: `) -> bool:`.
- **L41:** (w `consecutive_low_enough`) Warunek `if` — gdy `len(scores) < n`.
- **L42:** (w `consecutive_low_enough`) Zwraca: `False`.
- **L43:** (w `consecutive_low_enough`) Zwraca: `all(s <= threshold for s in scores[-n:])`.
- **L46:** Dekorator `@dataclass` (np. route FastAPI, fixture, dataclass).
- **L47:** Definicja klasy `Conversation`.
- **L48:** (w `Conversation`) Wykonuje: `problem: str`.
- **L49:** (w `Conversation`) Wykonuje: `config: SenseiConfig`.
- **L50:** (w `Conversation`) Przypisanie `messages: list[dict]` ← `field(default_factory=list)`.
- **L51:** (w `Conversation`) Przypisanie `prompt_scores: list[int]` ← `field(default_factory=list)`.
- **L52:** (w `Conversation`) Przypisanie `last_code: str` ← `""`.
- **L53:** (w `Conversation`) Przypisanie `prelab_passed: bool` ← `False`.
- **L54:** (w `Conversation`) Przypisanie `prelab_attempts: int` ← `0`.
- **L55:** (w `Conversation`) Przypisanie `last_prelab_score: float | None` ← `None`.
- **L56:** (w `Conversation`) Przypisanie `tokens_used_total: int` ← `0`.
- **L57:** (w `Conversation`) Przypisanie `ide_events: list[dict[str, Any]]` ← `field(default_factory=list)`.
- **L58:** (w `Conversation`) Przypisanie `reveal_count: int` ← `0`.
- **L59:** (w `Conversation`) Przypisanie `summary_generated: bool` ← `False`.
- **L60:** (w `Conversation`) Przypisanie `last_summary: dict[str, Any] | None` ← `None`.
- **L61:** (w `Conversation`) Przypisanie `goal_progress: list[dict[str, str]]` ← `field(default_factory=list)`.
- **L62:** (w `Conversation`) Przypisanie `unlocked_checkpoints: list[str]` ← `field(default_factory=list)`.
- **L63:** (w `Conversation`) Przypisanie `idempotency: dict[str, dict[str, Any]]` ← `field(default_factory=dict)`.
- **L64:** (w `Conversation`) Przypisanie `pinned_identifiers: list[str]` ← `field(default_factory=list)`.
- **L65–L67:** (w `Conversation`) Wyrażenie wieloliniowe — L65: Przypisanie `created_at: datetime` ← `field(`. | L66: Przypisanie `default_factory` ← `lambda: datetime.now(timezone.utc)`. | L67: Zamknięcie wyrażenia (`)`).
- **L68–L70:** (w `Conversation`) Wyrażenie wieloliniowe — L68: Przypisanie `last_active_at: datetime` ← `field(`. | L69: Przypisanie `default_factory` ← `lambda: datetime.now(timezone.utc)`. | L70: Zamknięcie wyrażenia (`)`).
- **L72:** Definicja funkcji/metody `remember_identifiers`, zwraca `None`.
- **L73:** Docstring: Keep student-stated code identifiers across compression.
- **L74:** (w `Conversation`) Przypisanie `seen` ← `{t.lower() for t in self.pinned_identifiers}`.
- **L75:** (w `Conversation`) Pętla `for` po `tok in tokens`.
- **L76:** (w `Conversation`) Przypisanie `key` ← `tok.lower()`.
- **L77:** (w `Conversation`) Warunek `if` — gdy `key in seen`.
- **L78:** (w `Conversation`) Przechodzi do kolejnej iteracji pętli (`continue`).
- **L79:** (w `Conversation`) Wykonuje: `seen.add(key)`.
- **L80:** (w `Conversation`) Wykonuje: `self.pinned_identifiers.append(tok)`.
- **L81:** (w `Conversation`) Warunek `if` — gdy `len(self.pinned_identifiers) >= limit`.
- **L82:** (w `Conversation`) Przerywa pętlę (`break`).
- **L84:** (w `Conversation`) Dekorator `@property` (np. route FastAPI, fixture, dataclass).
- **L85:** Definicja funkcji/metody `is_frustrated`, zwraca `bool`.
- **L86:** (w `Conversation`) Zwraca: `is_frustrated(self.prompt_scores)`.
- **L88:** Definicja funkcji/metody `touch`, zwraca `None`.
- **L89:** (w `Conversation`) Przypisanie `self.last_active_at` ← `datetime.now(timezone.utc)`.
- **L91:** Definicja funkcji/metody `ensure_goal_progress_defaults`, zwraca `None`.
- **L92:** (w `Conversation`) Warunek `if` — gdy `self.goal_progress`.
- **L93:** (w `Conversation`) Zwraca `None`.
- **L94–L97:** (w `Conversation`) Wyrażenie wieloliniowe — L94: Przypisanie `self.goal_progress` ← `[`. | L95: Wykonuje: `{"goal": g, "status": "not_started"}`. | L96: Pętla `for` po `g in (self.config.learningContext.goals or [])`. | L97: Zamknięcie wyrażenia (`]`).
