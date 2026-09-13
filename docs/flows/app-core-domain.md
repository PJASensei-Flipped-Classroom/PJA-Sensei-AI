# Przebiegi: app/ — core i domain

Infrastruktura (`core`) oraz modele/wyjątki domenowe bez FastAPI/LLM.

### `app/__init__.py`

- **Rola:** Znacznik pakietu głównego aplikacji (pusty).
- **Przebieg funkcjonalności:**
  1. Plik istnieje wyłącznie jako marker pakietu Python `app`.
  2. Nie eksportuje symboli ani nie inicjalizuje stanu.

### `app/main.py`

- **Rola:** Fabryka FastAPI: lifespan kontenera DI, middleware, routery publiczne i chronione; eksport `app` dla uvicorn.
- **Przebieg funkcjonalności:**
  1. Importuje routery API, auth, rate limit, CORS i `AppContainer`.
  2. `create_app(container=None)` buduje lifespan: przy starcie ustawia `app.state.container` (podany lub `init_container()`), przy shutdown wywołuje opcjonalne `container.shutdown()`.
  3. Tworzy `FastAPI` z tytułem PJA-Sensei i lifespanem.
  4. Dokłada `RequestIdMiddleware` oraz `CORSMiddleware` (origins z config; expose `X-Message-Id` / `X-Request-Id`).
  5. Rejestruje handlery wyjątków domenowych (`register_exception_handlers`).
  6. Podłącza publiczny router `health` (UI, `/health`, `/metrics`).
  7. Buduje router chroniony `require_auth` + `enforce_rate_limit` i dołącza: config_validate, analytics, conversations, messages, prelab.
  8. Na module: `app = create_app()` — punkt wejścia `uvicorn app.main:app`.
- **Główne zależności:** app.api.*, app.application.container, app.core.auth/config

### `app/core/__init__.py`

- **Rola:** Docstring pakietu infrastruktury (settings, auth, metrics, rate limiting).
- **Przebieg funkcjonalności:**
  1. Nie zawiera logiki — tylko opis pakietu.

### `app/core/config.py`

- **Rola:** Centralna konfiguracja pydantic-settings + eksport stałych używanych w całym module.
- **Przebieg funkcjonalności:**
  1. Klasa `Settings` czyta `.env` (UTF-8, extra ignore, case-insensitive).
  2. Pola: OpenRouter, webhooki telemetry/summary, CORS, JWT, rate limit, cache, TTL/cap konwersacji, `security_fail_closed`.
  3. Property: `cors_origin_list`, `conversation_ttl`, `resolved_summary_webhook_url`.
  4. `get_settings()` z `@lru_cache` tworzy singleton.
  5. Moduł eksportuje stałe wielkimi literami konsumowane przez adaptery, core i API.
- **Główne zależności:** pydantic_settings, plik `.env`

### `app/core/auth.py`

- **Rola:** Zależność FastAPI walidująca Bearer JWT gdy `AI_AUTH_ENABLED`.
- **Przebieg funkcjonalności:**
  1. HTTPBearer bez auto_error — brak tokena obsługiwany ręcznie.
  2. Auth wyłączony → zwraca `None` (passthrough).
  3. Auth włączony, pusty secret → 500 Auth misconfigured.
  4. Brak/nie-Bearer → 401; dekodyfikacja JWT; wymaga claim `sub`.
- **Główne zależności:** app.core.config, PyJWT

### `app/core/metrics.py`

- **Rola:** W-processowy kolektor metryk z eksportem snapshot JSON i Prometheus text.
- **Przebieg funkcjonalności:**
  1. `MetricsCollector` trzyma liczniki chronione `threading.Lock`.
  2. `inc` / `snapshot` (hit-rate, avg tokens) / `prometheus_text(extra)`.
  3. Globalny singleton `metrics` używany w całym serwisie.

### `app/core/rate_limit.py`

- **Rola:** Sliding-window limiter (60 s) per klucz + helper IP/conversation.
- **Przebieg funkcjonalności:**
  1. `RateLimiter.check` usuwa stare hity; przy limicie → 429 + Retry-After i metryka.
  2. Przy >10k kluczy czyści stale wpisy.
  3. `client_key`: `conv:{id}` lub IP (X-Forwarded-For / client.host).
  4. Globalny `rate_limiter` z `RATE_LIMIT_PER_MINUTE`.
- **Główne zależności:** app.core.config/metrics

### `app/domain/__init__.py`

- **Rola:** Pakiet modeli domenowych bez zależności HTTP/LLM.
- **Przebieg funkcjonalności:**
  1. Tylko docstring pakietu.

### `app/domain/exceptions.py`

- **Rola:** Wyjątki domenowe mapowane na HTTP w warstwie API.
- **Przebieg funkcjonalności:**
  1. `UnknownConversation` → 404.
  2. `PrelabRequired` / `TokenBudgetExceeded` → 403 z payloadem czatu.
  3. `RevealNotAllowed(detail)` → 403 + detail.

### `app/domain/sensei.py`

- **Rola:** Modele Pydantic `SenseiConfig` oraz kontekstu kodu IDE.
- **Przebieg funkcjonalności:**
  1. Materiały, cele, persona/behavior, IDE restrictions, pre-lab, checkpointy.
  2. `SenseiConfig` agreguje konfigurację labu (język, budżet tokenów, kryteria).
  3. `CodeContext` (+ selection, diagnostics, open_files) — snapshot IDE w wiadomościach.
- **Główne zależności:** pydantic

### `app/domain/conversation.py`

- **Rola:** Agregat in-memory `Conversation` + helpery frustracji/scoringu.
- **Przebieg funkcjonalności:**
  1. Heurystyki low-score / frustration streak / średnia ostatnich score.
  2. `Conversation` trzyma historię, prelab, tokens, IDE events, reveal, summary, goals, idempotency, pinne identyfikatory, TTL timestamps.
  3. `remember_identifiers`, `touch()`, `ensure_goal_progress_defaults()`.
- **Główne zależności:** app.domain.sensei
