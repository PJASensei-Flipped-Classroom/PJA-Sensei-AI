# Przebiegi funkcjonalności — PJA-Sensei AI Module

Dokumentacja **przebiegu odpowiedzialności** plików źródłowych (język: polski).
Nie jest to katalog linia-po-linii — ten jest w [FILE_CATALOG.md](FILE_CATALOG.md).

Pominięto: `.venv/`, `__pycache__/`, sekrety (`.env`), plany `.cursor/`.

## Części

| Część | Plik | Zakres |
|-------|------|--------|
| app — core i domain | [flows/app-core-domain.md](flows/app-core-domain.md) | main, core, domain |
| app — adapters | [flows/app-adapters.md](flows/app-adapters.md) | LLM, RAG, cache, security, webhooks |
| app — application | [flows/app-application.md](flows/app-application.md) | use-cases / serwisy |
| app — api | [flows/app-api.md](flows/app-api.md) | HTTP, schemas, routers |
| tests | [flows/tests.md](flows/tests.md) | pytest + live |
| static / scripts / schemas | [flows/static-scripts-schemas.md](flows/static-scripts-schemas.md) | UI, dump YAML, kontrakty |

## Indeks plików (cel 1–2 zdania)

- [`app/__init__.py`](flows/app-core-domain.md) — Marker pakietu głównego.
- [`app/main.py`](flows/app-core-domain.md) — Fabryka FastAPI, lifespan kontenera, CORS, routery publiczne/chronione.
- [`app/core/__init__.py`](flows/app-core-domain.md) — Pakiet infrastruktury (settings, auth, metrics, rate limit).
- [`app/core/config.py`](flows/app-core-domain.md) — Ustawienia env i eksport stałych konfiguracyjnych.
- [`app/core/auth.py`](flows/app-core-domain.md) — Walidacja Bearer JWT gdy AI_AUTH_ENABLED.
- [`app/core/metrics.py`](flows/app-core-domain.md) — Kolektor metryk in-process + eksport Prometheus.
- [`app/core/rate_limit.py`](flows/app-core-domain.md) — Sliding-window rate limiter per IP/konwersacja.
- [`app/domain/__init__.py`](flows/app-core-domain.md) — Pakiet modeli domenowych bez HTTP/LLM.
- [`app/domain/exceptions.py`](flows/app-core-domain.md) — Wyjątki domenowe mapowane na HTTP.
- [`app/domain/sensei.py`](flows/app-core-domain.md) — Modele SenseiConfig i CodeContext (IDE).
- [`app/domain/conversation.py`](flows/app-core-domain.md) — Agregat Conversation + heurystyki frustracji.
- [`app/adapters/__init__.py`](flows/app-adapters.md) — Pakiet adapterów I/O.
- [`app/adapters/llm_openrouter.py`](flows/app-adapters.md) — Klient OpenRouter i estymacja tokenów.
- [`app/adapters/cache_memory.py`](flows/app-adapters.md) — Exact-match cache odpowiedzi (TTL/LRU).
- [`app/adapters/security.py`](flows/app-adapters.md) — Brama promptów: regex + model security.
- [`app/adapters/webhooks.py`](flows/app-adapters.md) — Outbound webhooki telemetry/summary.
- [`app/adapters/rag_chroma.py`](flows/app-adapters.md) — RAG Chroma: load materiałów i retrieval.
- [`app/application/__init__.py`](flows/app-application.md) — Pakiet przypadków użycia.
- [`app/application/container.py`](flows/app-application.md) — Kontener DI łączący adaptery i serwisy.
- [`app/application/chat.py`](flows/app-application.md) — Czat: send, cache, regenerate, reveal hint.
- [`app/application/response_pipeline.py`](flows/app-application.md) — Parsowanie odpowiedzi LLM, kary za kod, kompresja historii.
- [`app/application/sessions.py`](flows/app-application.md) — Sesje: TTL, state, export, idempotency, delete.
- [`app/application/prompts.py`](flows/app-application.md) — System prompt i formatowanie kontekstu kodu.
- [`app/application/stream.py`](flows/app-application.md) — Streaming NDJSON odpowiedzi czatu.
- [`app/application/prelab.py`](flows/app-application.md) — Quiz pre-lab: get/submit/generate.
- [`app/application/review.py`](flows/app-application.md) — Sokratyczny review kodu.
- [`app/application/summary.py`](flows/app-application.md) — Podsumowanie sesji dla wykładowcy.
- [`app/application/goals.py`](flows/app-application.md) — Ocena celów i checkpointów.
- [`app/application/analytics.py`](flows/app-application.md) — Korelacje między sesjami.
- [`app/api/__init__.py`](flows/app-api.md) — Pakiet warstwy HTTP.
- [`app/api/deps.py`](flows/app-api.md) — Kontener, rate limit, walidacja wiadomości.
- [`app/api/errors.py`](flows/app-api.md) — Handlery wyjątków i payloady blokad.
- [`app/api/guards.py`](flows/app-api.md) — Guardy konwersacji, file-context, safety.
- [`app/api/middleware.py`](flows/app-api.md) — Middleware X-Request-Id.
- [`app/api/schemas/__init__.py`](flows/app-api.md) — Re-eksport schematów request/response.
- [`app/api/schemas/requests.py`](flows/app-api.md) — Modele ciał żądań HTTP.
- [`app/api/schemas/responses.py`](flows/app-api.md) — Modele odpowiedzi HTTP.
- [`app/api/routers/__init__.py`](flows/app-api.md) — Marker pakietu routerów.
- [`app/api/routers/health.py`](flows/app-api.md) — UI, health, metrics.
- [`app/api/routers/analytics.py`](flows/app-api.md) — Endpoint korelacji analytics.
- [`app/api/routers/config_validate.py`](flows/app-api.md) — Walidacja SenseiConfig.
- [`app/api/routers/prelab.py`](flows/app-api.md) — Trasy pre-lab.
- [`app/api/routers/messages.py`](flows/app-api.md) — Trasy wiadomości i stream.
- [`app/api/routers/conversations.py`](flows/app-api.md) — Cykl życia konwersacji i endpointy sesji.
- [`tests/__init__.py`](flows/tests.md) — Marker pakietu testów.
- [`tests/conftest.py`](flows/tests.md) — Fixtury TestClient i mock LLM.
- [`tests/test_api_asgi.py`](flows/tests.md) — ASGI happy-path i bramki (offline).
- [`tests/test_api_edges.py`](flows/tests.md) — Krawędzie API: auth, limit, budget, …
- [`tests/test_cache_and_security.py`](flows/tests.md) — Cache, frustracja, security fail-closed.
- [`tests/test_code_penalty.py`](flows/tests.md) — Heurystyka kary za ujawniony kod.
- [`tests/test_stream_extract.py`](flows/tests.md) — Extractor strumienia pola answer.
- [`tests/live/__init__.py`](flows/tests.md) — Marker suite live.
- [`tests/live/test_all.py`](flows/tests.md) — Orkiestrator offline+live ewaluacji.
- [`tests/live/test_memory.py`](flows/tests.md) — Scenariusze live S1–S24.
- [`static/index.html`](flows/static-scripts-schemas.md) — Tester UI w przeglądarce.
- [`scripts/dump_openapi_yaml.py`](flows/static-scripts-schemas.md) — Dump openapi.json → yaml.
- [`schemas/sensei-config.schema.json`](flows/static-scripts-schemas.md) — JSON Schema SenseiConfig.
- [`schemas/openapi.json`](flows/static-scripts-schemas.md) — Kontrakt OpenAPI 3 (JSON).
- [`schemas/openapi.yaml`](flows/static-scripts-schemas.md) — Kontrakt OpenAPI 3 (YAML).

**Liczba opisanych plików:** 59

## Uwagi

- Każdy plik w częściach `docs/flows/` ma: **Rola**, numerowany **Przebieg funkcjonalności**, opcjonalnie **Główne zależności**.
- Schematy JSON/YAML opisane strukturalnie (JSON nie wspiera komentarzy w źródle).
- Kod aplikacji po dokumentacji pozostaje bez tymczasowych komentarzy pomocniczych.
