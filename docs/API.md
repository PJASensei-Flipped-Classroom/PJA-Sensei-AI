# API — endpointy (backend)

Kontrakt HTTP mikroserwisu PJA-Sensei.

- Swagger na żywo: `/docs`
- Snapshot: [`schemas/openapi.yaml`](../schemas/openapi.yaml)
- Uruchomienie: [URUCHOMIENIE.md](URUCHOMIENIE.md)

`…` = `/conversations/{conversation_id}`.

## Publiczne vs chronione

| | Ścieżki | Middleware |
|--|---------|------------|
| **Publiczne** | `/`, `/scenarios`, `/health`, `/healthz`, `/metrics`, `/metrics/prometheus` | bez JWT / rate limit |
| **Chronione** | `/conversations…`, `/validate-config` | `require_auth` + `enforce_rate_limit` |

Gdy `AI_AUTH_ENABLED=true`: Bearer JWT. Lokalnie zwykle `false`.

Propaguj `X-Request-Id` (korelacja z telemetrią).

> **Naming:** `learningContext.goals` i `agentBehavior.mode: "review"` to pola **SenseiConfig**, nie osobne trasy `/goals` / `/review`.

---

## Mapa endpointów

| Metoda | Ścieżka | Request (kluczowe) | Response (kluczowe) | Typowe błędy |
|--------|---------|--------------------|---------------------|--------------|
| GET | `/` | — | `index.html` | 404 brak pliku |
| GET | `/scenarios` | — | `scenarios.html` | 404 |
| GET | `/healthz` | — | `{ status }` | — |
| GET | `/health` | — | `status`, `llm_configured`, `chroma_ok`, conv/cache | **503** degraded |
| GET | `/metrics` | — | JSON counters | — |
| GET | `/metrics/prometheus` | — | text Prometheus | — |
| POST | `/validate-config` | `{ config }` | `valid`, `pydantic_errors`, `schema_errors`, `schema_unavailable` | 401/429 |
| POST | `/conversations` | `problem_description`, `config` | `conversation_id`, `prelab_required`, `ide_restrictions` | 401/422/429 |
| GET | `/conversations/{id}` | — | stan sesji (+ `goal_progress`) | 404 |
| DELETE | `/conversations/{id}` | — | `status`, opcjonalnie `summary` | 404 |
| GET | `…/messages` | — | `{ conversation_id, messages }` | 404 |
| POST | `…/messages` | `MessageRequest` | `MessageResponse` | 403/404 + bramki |
| POST | `…/messages/stream` | `MessageRequest` | NDJSON `token` → `final` | j.w. |
| POST | `…/messages/{mid}/feedback` | `rating` 1–5, `comment?` | `status`, `message_id`, `rating` | 404 |
| GET | `…/prelab` | — | pytania (`question`), **bez** keywords | 404 |
| POST | `…/prelab` | `answers[]` | `passed`, `score`, `attempts`, … | 404 |
| GET | `…/restrictions` | — | flagi IDE + prelab | 404 |
| GET | `…/export` | — | dump sesji | 404 |
| GET | `…/checkpoints` | — | `{ checkpoints[] }` | 404 |
| POST | `…/events` | `type`, `meta?` | `{ status, event }` | 404/422 |
| POST | `…/summary` | — | summary ROI (LLM) | 404 |
| POST | `…/hints/reveal` | `focus?`, `code_context?` | `hint`, `reveal_count`, … | **403**/404 |

**Side effects przy starcie:** purge TTL starych sesji, opcjonalnie RAG w tle.  
**Soft DELETE:** próba summary + cleanup RAG + webhook.

---

## MessageRequest / MessageResponse

**Request**

- `question` (string)
- `code_context` — `current_file_name`, `current_code`, `error_logs`, …
- `client_message_id` (opcjonalnie) — idempotency

**Response (skrót)**

- `message_id`, `answer`, `prompt_score` (1–10), `prompt_feedback`
- `tokens_used`, `penalty_applied`, `sources`, `suggested_next_step`
- `goal_progress[]`, `next_checkpoint`, `model`, `debug_info`

UI liczy **Cel labu X/10** z `goal_progress` (done/total × 10).  
`prompt_score` to osobno jakość pytania tury.

---

## Bramki czatu

Kolejność (uproszczenie): istnienie sesji → prelab → budżet tokenów → (dalej security / pedagogy / LLM).

| Gate | HTTP | Shape |
|------|------|--------|
| Prelab niezaliczony | **403** | `message_id: prelab_required` (PL/EN z `config.language`) |
| `maxTokensPerSession` | **403** | `message_id: token_budget_exceeded` |
| Reveal bez streaku / po quota | **403** | `detail` tekstowy |
| Injection / jailbreak | **200** | `message_id: blocked` |
| Pusty plik + `requireFileContext` (debug) | **200** | `message_id: rejected` |
| Rate limit API | **429** | — |
| Brak / zły JWT | **401** | — |
| Brak sesji | **404** | — |
| Zły SenseiConfig | **422** | validate / start |

---

## Stream (NDJSON)

`POST …/messages/stream` — linie JSON:

1. `{ "type": "token", "text": "…" }` — przyrosty `answer`
2. `{ "type": "final", …MessageResponse }` — final + telemetria

---

## SenseiConfig

- Kontrakt IDE: **camelCase** (`learningContext`, `agentBehavior`, `preLab`, `maxTokensPerSession`, …).
- Schema: [`schemas/sensei-config.schema.json`](../schemas/sensei-config.schema.json).
- Start sesji i `/validate-config` używają tej samej walidacji (Pydantic + JSON Schema; brak schema → `valid: false`).

---

## Webhooki

| Event | Kiedy | URL |
|-------|-------|-----|
| `message` | sync + stream `final` | `TELEMETRY_URL` |
| `ide_event` | `POST …/events` | `TELEMETRY_URL` |
| `session_summary` | summary / soft DELETE | `SUMMARY_WEBHOOK_URL` → fallback telemetry |

Implementacja: `app/api/telemetry.py` → `adapters/webhooks.py`. Błędy webhooka nie wywalają requestu klienta.

---

## Po zmianie HTTP / schematów

```powershell
python -m scripts.export_openapi
```

Commituj zaktualizowane `schemas/openapi.json` / `.yaml`.

---

## Usunięte (nie wracać bez decyzji produktowej)

- `GET /analytics/correlations`
- `POST …/review`, `…/goals/assess`, `…/messages/{id}/regenerate`, `…/prelab/generate`
