# API (endpointy i przykłady)

Kontrakt HTTP mikroserwisu PJA-Sensei. Warstwy i happy-path: [ARCHITECTURE.md](ARCHITECTURE.md).  
Swagger: `/docs`. Snapshot: [`schemas/openapi.yaml`](../schemas/openapi.yaml).

**Auth:** trasy chronione wymagają Bearer JWT gdy `AI_AUTH_ENABLED=true`, plus rate limit (`RATE_LIMIT_PER_MINUTE`).  
**Publiczne:** `/`, `/healthz`, `/health`, `/metrics`, `/metrics/prometheus`.

`…` = `/conversations/{conversation_id}`.

Propaguj `X-Request-Id` (korelacja z telemetrią Spring).

> **Naming:** `learningContext.goals` i `agentBehavior.mode: "review"` to pola **SenseiConfig**, nie usunięte trasy `/goals/assess` / `/review`.

---

## Mapa endpointów

| Metoda | Ścieżka | Auth | Request | Response (kluczowe) | Błędy | Use-case | Side effects |
|--------|---------|------|---------|---------------------|-------|----------|--------------|
| GET | `/` | — | — | `static/index.html` | 404 jeśli brak pliku | — | — |
| GET | `/healthz` | — | — | `{ status: ok }` | — | liveness | — |
| GET | `/health` | — | — | `status`, `conversations`, `cache_size`, `chroma_ok`, `llm_configured` | 503 gdy degraded | readiness | **bez** purge TTL |
| GET | `/metrics` | — | — | JSON counters + conv/cache | — | `metrics` | — |
| GET | `/metrics/prometheus` | — | — | text/plain Prometheus | — | `metrics` | — |
| POST | `/validate-config` | JWT+RL | `{ config }` SenseiConfig | `valid`, `errors` | 401/429 | jsonschema | — |
| POST | `/conversations` | JWT+RL | `problem_description`, `config` | `conversation_id`, `prelab_required`, `ide_restrictions` | 401/429 | `SessionService.start` | **purge TTL**, cap, tło RAG |
| GET | `/conversations/{id}` | JWT+RL | — | stan sesji | 404 | `get_session_state` | — |
| DELETE | `/conversations/{id}` | JWT+RL | — | `status`, opcjonalne `summary` | 404 | `delete_conversation` | summary LLM, RAG delete, webhook |
| GET | `…/messages` | JWT+RL | — | `{ conversation_id, messages }` | 404 | `get_message_history` | — |
| POST | `…/messages` | JWT+RL | `MessageRequest` | `MessageResponse` | 403/404 + bramki | `ChatService.send_message` | cache, webhook `message` |
| POST | `…/messages/stream` | JWT+RL | `MessageRequest` | NDJSON `{type:token\|final}` | j.w. | `StreamService` | webhook na `final` |
| POST | `…/messages/{mid}/feedback` | JWT+RL | `rating`, `comment?` | `status`, `message_id`, `rating` | 404 | `record_message_feedback` | — |
| GET | `…/prelab` | JWT+RL | — | pytania **bez** keywords | 404 | `PrelabService.get` | — |
| POST | `…/prelab` | JWT+RL | answers | score, passed, attempts | 404 | `PrelabService.submit` | `prelab_passed` |
| GET | `…/restrictions` | JWT+RL | — | flagi IDE + prelab | 404 | `get_restrictions` | — |
| GET | `…/export` | JWT+RL | — | pełny dump sesji | 404 | `export_conversation` | — |
| GET | `…/checkpoints` | JWT+RL | — | `{ conversation_id, checkpoints[] }` | 404 | `get_checkpoints` | może dopisać `unlocked_checkpoints` |
| POST | `…/events` | JWT+RL | `IdeEventRequest` | `{ status, event }` | 404 | `record_ide_event` | webhook `ide_event` |
| POST | `…/summary` | JWT+RL | — | summary ROI (LLM JSON) | 404 | `SummaryService` | webhook `session_summary` |
| POST | `…/hints/reveal` | JWT+RL | `RevealHintRequest` | `hint`, `reveal_count`, … | 403/404 | `ChatService.reveal_hint` | quota `MAX_REVEALS_PER_SESSION` |

Bramki przed chatem: [ARCHITECTURE.md — Bramki](ARCHITECTURE.md#bramki-wiadomości).

---

## Webhooki

| Event | Kiedy | URL |
|-------|-------|-----|
| `message` | sync final + stream `{type:final}` | `TELEMETRY_URL` |
| `ide_event` | `POST …/events` | `TELEMETRY_URL` |
| `session_summary` | `POST …/summary` lub soft DELETE | `SUMMARY_WEBHOOK_URL` (fallback → telemetry) |

Implementacja: `app/api/telemetry.py` → `app/adapters/webhooks.py`. Nie rzuca do callera.

---

## MessageRequest (skrót)

- `question` (str)
- `code_context` (`CodeContext`: plik, kod, logi, …)
- `client_message_id` (opcjonalnie — idempotency)

SenseiConfig: **camelCase** IDE — [`schemas/sensei-config.schema.json`](../schemas/sensei-config.schema.json).

---

## Usunięte (API slim — nie wracać bez decyzji)

- `GET /analytics/correlations`
- `POST …/review`
- `POST …/goals/assess`
- `POST …/messages/{id}/regenerate`
- `POST …/prelab/generate`

Nie mylić z `learningContext.goals`, `checkpoints`, `agentBehavior.mode: "review"`.

---

## Sesje

- In-memory — trwały store wymaga decyzji produktowej.
- TTL purge przy **starcie** nowej sesji (`CONVERSATION_TTL_SECONDS`), nie przy `/health`.
- Cap: `MAX_CONVERSATIONS`.

---

## Przykłady

Base URL: `http://127.0.0.1:8000`.

### 1. Start session

`POST /conversations`

```json
{
  "problem_description": "Napisz kontroler REST zwracający użytkownika w JSON.",
  "config": {
    "learningContext": {
      "goals": ["Utwórz @RestController", "Zwróć JSON"],
      "referenceMaterials": [
        { "type": "doc", "title": "Spring REST", "url": "https://spring.io/guides/gs/rest-service/" }
      ]
    },
    "agentBehavior": {
      "persona": { "role": "mentor", "tone": "cierpliwy" },
      "strictRules": ["Nie podawaj gotowego kodu"],
      "mode": "debug"
    },
    "language": "pl",
    "checkpoints": [
      { "id": "cp1", "after_goal": "Utwórz @RestController", "hint": "Odblokuj testy jednostkowe kontrolera" }
    ],
    "preLab": {
      "enabled": true,
      "max_attempts": 3,
      "hint_after_fail": "Przypomnij sobie, że REST opiera się na HTTP.",
      "questions": [
        { "id": "q1", "prompt": "Co to REST?", "expected_keywords": ["http", "api"] }
      ]
    }
  }
}
```

### 2. Pre-lab then chat (rich CodeContext)

`POST /conversations/{id}/prelab` → potem `POST /conversations/{id}/messages`

```json
{
  "question": "Dlaczego dostaję 404?",
  "client_message_id": "vscode-msg-001",
  "code_context": {
    "current_file_name": "MyController.java",
    "current_code": "public class MyController {}",
    "workspace_root": "/lab/project",
    "selection": { "start_line": 1, "end_line": 1, "text": "public class MyController {}" },
    "diagnostics": [
      { "severity": "error", "message": "cannot find symbol RestController", "line": 1, "file": "MyController.java" }
    ],
    "open_files": [
      { "path": "pom.xml", "content": "<project>...</project>", "language": "xml" }
    ],
    "error_logs": "404 Not Found"
  }
}
```

Stream: to samo ciało na `POST …/messages/stream` → NDJSON `{"type":"token"}` potem `{"type":"final",…}`. Sync i stream emitują telemetry `event: message`.

### 3. IDE events + export + soft close

`POST /conversations/{id}/events`

```json
{ "type": "copy_blocked", "meta": { "source": "chat" } }
```

`GET …/export` — pełny dump. `DELETE …` — soft summary + webhook + cleanup RAM/Chroma.

### 4. Reveal hint

`POST …/hints/reveal` — po streaku niskich score / frustracji; quota sesji. Response: `hint`, `reveal_count`, `reveals_remaining` (bez pełnego kodu rozwiązania).
