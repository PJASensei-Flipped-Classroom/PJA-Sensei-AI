# Katalog plików — PJA-Sensei AI Module

Pełny katalog **linia-po-linii** (język: polski) wszystkich istotnych plików kodu, testów, schematów, static, skryptów i dokumentacji powiązanej z kodem.

Pominięto: `.venv/`, `__pycache__/`, `.git/`, `.idea/`, cache, pliki binarne, lokalny `.env` (sekrety).

Dokument podzielono na części w `docs/catalog/`, bo pełny opis przekracza wygodny rozmiar jednego pliku.

Linki w indeksie używają ścieżek od roota workspace (`/docs/catalog/...`), żeby działały po Ctrl+klik w Cursorze.

## Przegląd struktury

```text
PJASensei_AI_Module/
├── app/                 # FastAPI: api / application / adapters / domain / core
├── static/              # tester UI
├── tests/               # pytest + tests/live
├── schemas/             # OpenAPI + SenseiConfig JSON Schema
├── docs/                # katalog plików + przykłady OpenAPI
├── scripts/             # narzędzia deweloperskie
├── Dockerfile / docker-compose.yml
├── requirements.txt / pytest.ini / README.md
└── .env.example / .gitignore / .dockerignore
```

Punkt wejścia: `uvicorn app.main:app`.

## Części katalogu

| Część | Plik | Zakres |
|-------|------|--------|
| Root i konfiguracja | [docs/catalog/root.md](/docs/catalog/root.md) | 8 plików |
| app/ — core i domain | [docs/catalog/app-core-domain.md](/docs/catalog/app-core-domain.md) | 11 plików |
| app/ — adapters | [docs/catalog/app-adapters.md](/docs/catalog/app-adapters.md) | 6 plików |
| app/ — application | [docs/catalog/app-application.md](/docs/catalog/app-application.md) | 12 plików |
| app/ — api | [docs/catalog/app-api.md](/docs/catalog/app-api.md) | 15 plików |
| tests/ | [docs/catalog/tests.md](/docs/catalog/tests.md) | 10 plików |
| schemas/ | [docs/catalog/schemas.md](/docs/catalog/schemas.md) | 3 pliki |
| static/, scripts/, docs/ | [docs/catalog/static-scripts-docs.md](/docs/catalog/static-scripts-docs.md) | 4 pliki |

## Indeks wszystkich opisanych ścieżek

- [`README.md`](/docs/catalog/root.md#readme-md)
- [`requirements.txt`](/docs/catalog/root.md#requirements-txt)
- [`Dockerfile`](/docs/catalog/root.md#dockerfile)
- [`docker-compose.yml`](/docs/catalog/root.md#docker-compose-yml)
- [`pytest.ini`](/docs/catalog/root.md#pytest-ini)
- [`.env.example`](/docs/catalog/root.md#env-example)
- [`.gitignore`](/docs/catalog/root.md#gitignore)
- [`.dockerignore`](/docs/catalog/root.md#dockerignore)
- [`app/__init__.py`](/docs/catalog/app-core-domain.md#app-init-py)
- [`app/main.py`](/docs/catalog/app-core-domain.md#app-main-py)
- [`app/core/__init__.py`](/docs/catalog/app-core-domain.md#app-core-init-py)
- [`app/core/config.py`](/docs/catalog/app-core-domain.md#app-core-config-py)
- [`app/core/auth.py`](/docs/catalog/app-core-domain.md#app-core-auth-py)
- [`app/core/metrics.py`](/docs/catalog/app-core-domain.md#app-core-metrics-py)
- [`app/core/rate_limit.py`](/docs/catalog/app-core-domain.md#app-core-rate-limit-py)
- [`app/domain/__init__.py`](/docs/catalog/app-core-domain.md#app-domain-init-py)
- [`app/domain/exceptions.py`](/docs/catalog/app-core-domain.md#app-domain-exceptions-py)
- [`app/domain/sensei.py`](/docs/catalog/app-core-domain.md#app-domain-sensei-py)
- [`app/domain/conversation.py`](/docs/catalog/app-core-domain.md#app-domain-conversation-py)
- [`app/adapters/__init__.py`](/docs/catalog/app-adapters.md#app-adapters-init-py)
- [`app/adapters/llm_openrouter.py`](/docs/catalog/app-adapters.md#app-adapters-llm-openrouter-py)
- [`app/adapters/cache_memory.py`](/docs/catalog/app-adapters.md#app-adapters-cache-memory-py)
- [`app/adapters/security.py`](/docs/catalog/app-adapters.md#app-adapters-security-py)
- [`app/adapters/webhooks.py`](/docs/catalog/app-adapters.md#app-adapters-webhooks-py)
- [`app/adapters/rag_chroma.py`](/docs/catalog/app-adapters.md#app-adapters-rag-chroma-py)
- [`app/application/__init__.py`](/docs/catalog/app-application.md#app-application-init-py)
- [`app/application/container.py`](/docs/catalog/app-application.md#app-application-container-py)
- [`app/application/chat.py`](/docs/catalog/app-application.md#app-application-chat-py)
- [`app/application/response_pipeline.py`](/docs/catalog/app-application.md#app-application-response-pipeline-py)
- [`app/application/sessions.py`](/docs/catalog/app-application.md#app-application-sessions-py)
- [`app/application/prompts.py`](/docs/catalog/app-application.md#app-application-prompts-py)
- [`app/application/stream.py`](/docs/catalog/app-application.md#app-application-stream-py)
- [`app/application/prelab.py`](/docs/catalog/app-application.md#app-application-prelab-py)
- [`app/application/review.py`](/docs/catalog/app-application.md#app-application-review-py)
- [`app/application/summary.py`](/docs/catalog/app-application.md#app-application-summary-py)
- [`app/application/goals.py`](/docs/catalog/app-application.md#app-application-goals-py)
- [`app/application/analytics.py`](/docs/catalog/app-application.md#app-application-analytics-py)
- [`app/api/__init__.py`](/docs/catalog/app-api.md#app-api-init-py)
- [`app/api/deps.py`](/docs/catalog/app-api.md#app-api-deps-py)
- [`app/api/errors.py`](/docs/catalog/app-api.md#app-api-errors-py)
- [`app/api/guards.py`](/docs/catalog/app-api.md#app-api-guards-py)
- [`app/api/middleware.py`](/docs/catalog/app-api.md#app-api-middleware-py)
- [`app/api/schemas/__init__.py`](/docs/catalog/app-api.md#app-api-schemas-init-py)
- [`app/api/schemas/requests.py`](/docs/catalog/app-api.md#app-api-schemas-requests-py)
- [`app/api/schemas/responses.py`](/docs/catalog/app-api.md#app-api-schemas-responses-py)
- [`app/api/routers/__init__.py`](/docs/catalog/app-api.md#app-api-routers-init-py)
- [`app/api/routers/health.py`](/docs/catalog/app-api.md#app-api-routers-health-py)
- [`app/api/routers/analytics.py`](/docs/catalog/app-api.md#app-api-routers-analytics-py)
- [`app/api/routers/config_validate.py`](/docs/catalog/app-api.md#app-api-routers-config-validate-py)
- [`app/api/routers/prelab.py`](/docs/catalog/app-api.md#app-api-routers-prelab-py)
- [`app/api/routers/messages.py`](/docs/catalog/app-api.md#app-api-routers-messages-py)
- [`app/api/routers/conversations.py`](/docs/catalog/app-api.md#app-api-routers-conversations-py)
- [`tests/__init__.py`](/docs/catalog/tests.md#tests-init-py)
- [`tests/conftest.py`](/docs/catalog/tests.md#tests-conftest-py)
- [`tests/test_api_asgi.py`](/docs/catalog/tests.md#tests-test-api-asgi-py)
- [`tests/test_api_edges.py`](/docs/catalog/tests.md#tests-test-api-edges-py)
- [`tests/test_cache_and_security.py`](/docs/catalog/tests.md#tests-test-cache-and-security-py)
- [`tests/test_code_penalty.py`](/docs/catalog/tests.md#tests-test-code-penalty-py)
- [`tests/test_stream_extract.py`](/docs/catalog/tests.md#tests-test-stream-extract-py)
- [`tests/live/__init__.py`](/docs/catalog/tests.md#tests-live-init-py)
- [`tests/live/test_all.py`](/docs/catalog/tests.md#tests-live-test-all-py)
- [`tests/live/test_memory.py`](/docs/catalog/tests.md#tests-live-test-memory-py)
- [`schemas/sensei-config.schema.json`](/docs/catalog/schemas.md#schemas-sensei-config-schema-json)
- [`schemas/openapi.json`](/docs/catalog/schemas.md#schemas-openapi-json)
- [`schemas/openapi.yaml`](/docs/catalog/schemas.md#schemas-openapi-yaml)
- [`static/index.html`](/docs/catalog/static-scripts-docs.md#static-index-html)
- [`scripts/dump_openapi_yaml.py`](/docs/catalog/static-scripts-docs.md#scripts-dump-openapi-yaml-py)
- [`docs/openapi-examples.md`](/docs/catalog/static-scripts-docs.md#docs-openapi-examples-md)
- `docs/FILE_CATALOG.md` — ten indeks

**Liczba opisanych plików:** 69

Pominięte z rekurencji: same pliki `docs/catalog/*.md` (części tego katalogu) — opisujemy kod i docs źródłowe, nie dokumentujemy dokumentacji w nieskończoność. Lokalny `.env` (sekrety) też pominięty; jest `.env.example`.

## Uwagi o konwencji opisu

- Każdy plik ma sekcję ze ścieżką, celem (1–3 zdania) i opisem **L{n}** / **L{a}–L{b}**.
- Importy są grupowane w bloki, ale każda linia importu jest wymieniona.
- Puste linie pomijamy w wypunktowaniu (nie wpływają na numerację).
- Nie wklejamy pełnych dumpów kodu — opisujemy znaczenie linii/bloków.
- Dla OpenAPI (`openapi.json` / `.yaml`): krótka mapa sekcji + opis każdej niepustej linii.
