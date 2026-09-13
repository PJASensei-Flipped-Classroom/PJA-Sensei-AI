# Przebiegi: app/ — api

Warstwa HTTP: deps, guards, errors, middleware, schematy Pydantic, routery.

### `app/api/__init__.py`

- **Rola:** Docstring pakietu warstwy HTTP.
- **Przebieg funkcjonalności:**
  1. Marker pakietu.

### `app/api/deps.py`

- **Rola:** Zależności FastAPI: kontener, rate limit, walidacja requestu wiadomości.
- **Przebieg funkcjonalności:**
  1. `init_container` / `get_container` — singleton AppContainer.
  2. `enforce_rate_limit` — klucz conv/IP.
  3. `validate_message_request`: metryka, exist, prelab/budget (przy budget soft summary), file-context, security gate → (conversation, error|None).
- **Główne zależności:** guards, errors, sessions, security, metrics

### `app/api/errors.py`

- **Rola:** Handlery wyjątków domenowych oraz payloady blokad prelab/budget.
- **Przebieg funkcjonalności:**
  1. `blocked_payload(language, kind)` — kształt MessageResponse dla 403.
  2. `register_exception_handlers`: UnknownConversation 404; Prelab/Budget 403; RevealNotAllowed 403 detail.
- **Główne zależności:** domain.exceptions, FastAPI

### `app/api/guards.py`

- **Rola:** Guardy: istnienie konwersacji, file-context, safety promptu.
- **Przebieg funkcjonalności:**
  1. `require_conversation` (HTTP 404) vs `get_conversation` (UnknownConversation).
  2. `requires_file_context` + `missing_file_context_response`.
  3. `ensure_prompt_safe` → MessageResponse blokady lub None.
- **Główne zależności:** SecurityService, schemas

### `app/api/middleware.py`

- **Rola:** Middleware X-Request-Id + ContextVar.
- **Przebieg funkcjonalności:**
  1. Czyta/ generuje request id; ustawia ContextVar i `request.state`.
  2. Dokłada nagłówek odpowiedzi `X-Request-Id`.

### `app/api/schemas/__init__.py`

- **Rola:** Re-eksport modeli request/response (`__all__`).
- **Przebieg funkcjonalności:**
  1. Ułatwia importy `from app.api.schemas import …`.

### `app/api/schemas/requests.py`

- **Rola:** Modele ciał żądań HTTP (Pydantic).
- **Przebieg funkcjonalności:**
  1. Start, Message (+ client_message_id), PreLab submit, Feedback, IdeEvent, ValidateConfig, RevealHint, Review.
  2. Osadza `SenseiConfig` / `CodeContext` z domain.
- **Główne zależności:** domain.sensei

### `app/api/schemas/responses.py`

- **Rola:** Modele odpowiedzi HTTP (`MessageResponse` i powiązane).
- **Przebieg funkcjonalności:**
  1. `DebugInfo`, `SourceRef`, `GoalProgressItem`, `MessageResponse` (message_id UUID default).

### `app/api/routers/__init__.py`

- **Rola:** Znacznik pakietu routerów (pusty).
- **Przebieg funkcjonalności:**
  1. Umożliwia `from app.api.routers import health, …`.

### `app/api/routers/health.py`

- **Rola:** Endpointy ops: tester UI `/`, `/health`, `/metrics`.
- **Przebieg funkcjonalności:**
  1. `GET /` → `static/index.html`.
  2. `GET /health` — purge stale, status, key configured, counts, chroma_ok.
  3. `GET /metrics` JSON lub Prometheus; alias `/metrics/prometheus`.
- **Główne zależności:** deps, metrics, cache/rag

### `app/api/routers/analytics.py`

- **Rola:** Eksperymentalny endpoint korelacji między sesjami.
- **Przebieg funkcjonalności:**
  1. `GET /analytics/correlations` → `analytics.build_correlations()`.

### `app/api/routers/config_validate.py`

- **Rola:** Walidacja SenseiConfig: Pydantic + JSON Schema draft 2020-12.
- **Przebieg funkcjonalności:**
  1. `POST /validate-config` zbiera pydantic_errors i schema_errors.
  2. Zwraca `valid` gdy obie ścieżki przechodzą (z tolerancją braku jsonschema).
- **Główne zależności:** SenseiConfig, schemas/sensei-config.schema.json

### `app/api/routers/prelab.py`

- **Rola:** Trasy quizu pre-lab: get / submit / generate.
- **Przebieg funkcjonalności:**
  1. GET/POST `/conversations/{id}/prelab`; POST `…/prelab/generate` (experimental).
  2. Delegacja do `PrelabService`; 500 przy nieoczekiwanych błędach generate.

### `app/api/routers/messages.py`

- **Rola:** Trasy wiadomości: lista, send, stream NDJSON, regenerate, feedback.
- **Przebieg funkcjonalności:**
  1. GET history; POST send z `validate_message_request` + webhook telemetry.
  2. POST stream → StreamingResponse NDJSON + X-Message-Id.
  3. Regenerate (experimental); feedback zapisuje student_feedback na message.
- **Główne zależności:** chat, stream, webhooks, deps

### `app/api/routers/conversations.py`

- **Rola:** Cykl życia sesji: start, state, export, events, delete, review/goals/hint/summary.
- **Przebieg funkcjonalności:**
  1. POST start → id + opcjonalne tło `rag.load_materials`.
  2. GET state/restrictions/export/checkpoints; POST events (+ webhook).
  3. DELETE soft-summary + webhook; experimental review/goals/reveal; POST summary + webhook.
- **Główne zależności:** sessions, goals, review, chat, summary, rag, webhooks
