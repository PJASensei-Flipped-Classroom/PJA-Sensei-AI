# Mapa plików

Co robi dany plik, za co odpowiada i z czym jest powiązany.

## Architektura (skrót)

Kierunek importów:

```text
api  →  application  →  ports / domain / core
                  ↘ adapters tylko w AppContainer (composition root)
```

Happy-path sesji: `POST /conversations` → opcjonalnie prelab → `messages` / `stream` → `summary` / `DELETE`.

**Security** (jailbreak) ≠ **pedagogy** (odmowa gotowca). Webhooki woła warstwa API (`telemetry`), nie kontener use-case’ów.

---

## Wejście aplikacji

| Plik | Rola | Odpowiedzialność | Powiązania |
|------|------|------------------|------------|
| [`app/main.py`](../app/main.py) | Composition root HTTP | `create_app()`, lifespan (`app.state.container`), CORS, middleware, montaż routerów | → `AppContainer`, `api.routers.*`, `errors`, `auth`, `rate_limit` |

---

## `app/core` — konfiguracja i ops

| Plik | Rola | Odpowiedzialność | Powiązania |
|------|------|------------------|------------|
| [`config.py`](../app/core/config.py) | Settings | Env (`.env`): LLM URL/model, auth, TTL, limity, `TRUST_X_FORWARDED_FOR` | Czytane przez adapters, rate_limit, auth |
| [`auth.py`](../app/core/auth.py) | JWT | `require_auth` gdy `AI_AUTH_ENABLED` | → `main` (protected router) |
| [`metrics.py`](../app/core/metrics.py) | Telemetria procesu | Liczniki (messages, cache, llm_errors, language_drift_retry, …) | → chat, stream, deps, health |
| [`rate_limit.py`](../app/core/rate_limit.py) | HTTP 429 | Sliding window + cleanup w lifespan; XFF tylko gdy trusted | → `main`, `config` |

---

## `app/domain` — reguły bez HTTP/LLM

| Plik | Rola | Odpowiedzialność | Powiązania |
|------|------|------------------|------------|
| [`sensei.py`](../app/domain/sensei.py) | SenseiConfig | Modele Pydantic (camelCase), prelab, checkpoints, CodeContext | → sessions, validate-config, DTO |
| [`conversation.py`](../app/domain/conversation.py) | Agregat sesji | Stan w RAM: messages, scores, goals, reveal, TTL touch | → sessions, chat, pipeline |
| [`exceptions.py`](../app/domain/exceptions.py) | Błędy domenowe | `PrelabRequired`, `TokenBudgetExceeded`, `RevealNotAllowed`, … | → sessions → `api/errors` |

---

## `app/ports` — kontrakty

| Plik | Rola | Odpowiedzialność | Powiązania |
|------|------|------------------|------------|
| [`ports/__init__.py`](../app/ports/__init__.py) | Protocoly | LLM, RAG, Cache, Security, Summary, ConversationRepository | Implementacje w `adapters/`; wstrzyknięcie w `container.py` |

---

## `app/adapters` — I/O

| Plik | Rola | Odpowiedzialność | Powiązania |
|------|------|------------------|------------|
| [`llm_openai.py`](../app/adapters/llm_openai.py) | Klient LLM | AsyncOpenAI-compatible (Ollama/LM Studio): chat + stream | ← ChatService, StreamService, Summary, Security (współdzielony client) |
| [`rag_chroma.py`](../app/adapters/rag_chroma.py) | RAG | Chroma + fetch URL (blokada SSRF/private IP), chunking | ← SessionService (load), ChatService (retrieve) |
| [`cache_memory.py`](../app/adapters/cache_memory.py) | Cache | Exact-match LRU + TTL | ← ChatService |
| [`security.py`](../app/adapters/security.py) | Jailbreak | Regex → heurystyki → klasyfikator LLM; `close()` | ← deps/guards wiadomości; client z LLM |
| [`conversations_memory.py`](../app/adapters/conversations_memory.py) | Repo sesji | Dict w RAM + TTL purge | ← SessionService |
| [`webhooks.py`](../app/adapters/webhooks.py) | HTTP POST | Telemetria / summary webhook; wspólny client | ← `api/telemetry` (nie AppContainer) |

---

## `app/application` — use-case’y

| Plik | Rola | Odpowiedzialność | Powiązania |
|------|------|------------------|------------|
| [`container.py`](../app/application/container.py) | DI | Tworzy adaptery + serwisy; `close()` | Tylko composition root (`main` lifespan) |
| [`dto.py`](../app/application/dto.py) | DTO request | MessageRequest, IdeEvent, Reveal, Feedback, Start… | ← api schemas re-export; nie importować z `api` w application |
| [`sessions.py`](../app/application/sessions.py) | Sesje | Start, stan, export, events, feedback, bramki prelab/budget, checkpoints | ← routery conversations; → rag, repo |
| [`chat.py`](../app/application/chat.py) | Czat sync | Prompt, cache, pedagogy, LLM, drift retry, reveal | ← messages router; → llm, rag, cache, sessions, pipeline |
| [`stream.py`](../app/application/stream.py) | Czat stream | NDJSON token→final, ta sama polityka 429 | ← messages/stream |
| [`prelab.py`](../app/application/prelab.py) | Quiz wstępny | Pytania publiczne + submit (keywords) | ← prelab router |
| [`summary.py`](../app/application/summary.py) | ROI summary | JSON summary + webhook payload fields | ← summary / soft DELETE |
| [`prompts.py`](../app/application/prompts.py) | System prompt | PL/EN szablony, tryby, scoring, language lock | ← chat / stream |
| [`pedagogy_gates.py`](../app/application/pedagogy_gates.py) | Gotowiec / recall | Odmowa dump kodu; pinned identifiers | ← chat (przed LLM) |
| [`response_pipeline.py`](../app/application/response_pipeline.py) | Post-process | Parse JSON, code penalty, drift detect, fallbacki, stream extractor | ← chat / stream |
| [`llm_errors.py`](../app/application/llm_errors.py) | 429 policy | Retry + fallback model; `is_rate_limit_error` | ← chat / stream |

---

## `app/api` — HTTP

| Plik | Rola | Odpowiedzialność | Powiązania |
|------|------|------------------|------------|
| [`deps.py`](../app/api/deps.py) | DI + bramki | `get_container`, `validate_message_request` | → sessions; ← messages |
| [`guards.py`](../app/api/guards.py) | Cienkie guardy | Mapowanie wyjątków / early reject | → errors / domain |
| [`errors.py`](../app/api/errors.py) | HTTP map | 403 prelab/budget (PL/EN), 404, reveal | ← domain exceptions |
| [`middleware.py`](../app/api/middleware.py) | Request ID | `X-Request-Id` | → main |
| [`telemetry.py`](../app/api/telemetry.py) | Background POST | Buduje eventy webhook | → adapters/webhooks |
| [`routers/health.py`](../app/api/routers/health.py) | Ops + UI | `/`, `/scenarios`, `/health*`, `/metrics*` | static HTML |
| [`routers/conversations.py`](../app/api/routers/conversations.py) | Sesja | start, get, delete, events, export, checkpoints, summary, reveal | → sessions, chat, summary |
| [`routers/messages.py`](../app/api/routers/messages.py) | Czat | GET/POST messages, stream, feedback | → chat, stream |
| [`routers/prelab.py`](../app/api/routers/prelab.py) | Prelab HTTP | GET pytania, POST answers | → PrelabService |
| [`routers/config_validate.py`](../app/api/routers/config_validate.py) | Walidacja config | Pydantic + JSON Schema; assert przy starcie | → sensei schema |
| [`schemas/requests.py`](../app/api/schemas/requests.py) | Re-export DTO | Alias do `application.dto` | FastAPI body models |
| [`schemas/responses.py`](../app/api/schemas/responses.py) | Response models | MessageResponse itp. | OpenAPI |

---

## UI, schematy, skrypty, testy

| Plik / ścieżka | Rola | Odpowiedzialność | Powiązania |
|----------------|------|------------------|------------|
| [`static/index.html`](../static/index.html) | Tester lab | Wykładowca + Student + Ops | ← `GET /` |
| [`static/scenarios.html`](../static/scenarios.html) | Runner S1–S9 | Karty z logiem odpowiedzi | ← `GET /scenarios` |
| [`schemas/sensei-config.schema.json`](../schemas/sensei-config.schema.json) | JSON Schema | Walidacja SenseiConfig (camelCase) | ← config_validate |
| [`schemas/openapi.yaml`](../schemas/openapi.yaml) | Snapshot OpenAPI | Kontrakt HTTP | ← `scripts/export_openapi` |
| [`scripts/export_openapi.py`](../scripts/export_openapi.py) | Eksport | Regeneracja openapi po zmianie routerów | `python -m scripts.export_openapi` |
| [`tests/conftest.py`](../tests/conftest.py) | Fixtures | container, client, mock LLM | offline pytest |
| [`tests/helpers.py`](../tests/helpers.py) | Helpery ASGI | start_session, msg_body, happy config | test_01…04 |
| [`tests/test_01_happy_path.py`](../tests/test_01_happy_path.py) | Warstwa happy | Pełna sesja → cel 10/10 | mock LLM |
| [`tests/test_02_struggle.py`](../tests/test_02_struggle.py) | Struggle | Reveal, checkpoint, theory | |
| [`tests/test_03_cheat.py`](../tests/test_03_cheat.py) | Cheat | Jailbreak, gotowiec, prelab brute | |
| [`tests/test_04_edges.py`](../tests/test_04_edges.py) | Edges | 401/429/budget/i18n/RAG SSRF… | |
| [`tests/live/`](../tests/live/) | Live S1–S9 | HTTP + prawdziwy LLM | registry + scenarios/* |

Szczegóły uruchamiania: [TESTY.md](TESTY.md).

---

## Szybkie „gdzie szukać”

| Chcę zmienić… | Zacznij od |
|---------------|------------|
| Prompt / język odpowiedzi | `application/prompts.py` |
| Bramkę gotowca | `application/pedagogy_gates.py` |
| Jailbreak | `adapters/security.py` |
| Nowy endpoint | `api/routers/*` + DTO w `application/dto.py` + OpenAPI export |
| Env / model | `.env` + `core/config.py` |
| Start DI | `application/container.py` |
