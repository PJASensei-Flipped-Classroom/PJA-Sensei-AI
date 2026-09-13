# PJA-Sensei AI Module

FastAPI microservice: Socratic coding mentor for Flipped Classroom labs (OpenRouter + in-memory sessions + Chroma RAG).

## Layout

```text
app/
  main.py              # create_app() + lifespan
  api/                 # routers, schemas, deps, middleware
  application/         # use-cases (chat, prelab, sessions, …)
  adapters/            # OpenRouter, Chroma, cache, webhooks
  domain/              # Conversation, SenseiConfig, exceptions
  core/                # settings, auth, metrics, rate limit
static/                # tester UI
tests/                 # pytest + tests/live HTTP suite
schemas/               # OpenAPI / SenseiConfig JSON Schema
```

## Quick start

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # set OPENROUTER_API_KEY
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Tester UI: http://127.0.0.1:8000/
- Swagger: http://127.0.0.1:8000/docs
- Health: `GET /health`
- Metrics: `GET /metrics` or `GET /metrics/prometheus`

## Docker Compose

```bash
docker compose up --build
```

## Tests

Offline (ASGI + unit, no OpenRouter): gates, auth JWT, rate limit, pre-lab, token budget,
idempotency, file-context, cache TTL, `SECURITY_FAIL_CLOSED`, stream extract, code penalty.

Live HTTP (needs `uvicorn` on `:8000` + LLM key): scenarios **S1–S24** in `tests/live/test_memory.py`
(theory, RAG, injection, cache, stream, memory, pre-lab, review, reveal, budget, file-context, 404, …).

```bash
# Full evaluation: offline pytest, then live S1–S24 if API is up (else SKIP live)
.\.venv\Scripts\python.exe -m tests.live.test_all

# Offline only
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m tests.live.test_all --offline-only

# Live subset / require live
.\.venv\Scripts\python.exe -m tests.live.test_all --only 23,24
.\.venv\Scripts\python.exe -m tests.live.test_memory --only 3,6,22
.\.venv\Scripts\python.exe -m tests.live.test_all --require-live
```

## API surface

**Happy-path (VS Code / lab):** start conversation → optional pre-lab → messages / stream → events → export or DELETE.

**Experimental** (tagged in OpenAPI): `/review`, `/hints/reveal`, `/goals/assess`, message regenerate, `/prelab/generate`, `/analytics/correlations`.

## Notable env flags

| Variable | Default | Meaning |
|----------|---------|---------|
| `AI_AUTH_ENABLED` | `false` | Require Bearer JWT |
| `SECURITY_FAIL_CLOSED` | `false` | Block chat if security LLM fails |
| `RATE_LIMIT_PER_MINUTE` | `30` | Sliding window on protected routes |
| `MAX_CONVERSATIONS` / `CONVERSATION_TTL_SECONDS` | `200` / `7200` | In-memory session limits |

See [docs/openapi-examples.md](docs/openapi-examples.md) for sample payloads.

## Documentation

- [docs/FUNCTIONAL_FLOWS.md](docs/FUNCTIONAL_FLOWS.md) — przebiegi funkcjonalności plików (części w `docs/flows/`)
- [docs/FILE_CATALOG.md](docs/FILE_CATALOG.md) — katalog plików po polsku (opis linia-po-linii; części w `docs/catalog/`)
- [docs/openapi-examples.md](docs/openapi-examples.md) — request/response examples
