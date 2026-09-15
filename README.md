# PJA-Sensei AI Module

FastAPI microservice: Socratic coding mentor for Flipped Classroom labs (local Ollama / OpenAI-compatible LLM + in-memory sessions + Chroma RAG).

## Layout

```text
app/
  main.py              # create_app() + lifespan (app.state.container)
  api/                 # routers, schemas, deps, middleware
  application/         # use-cases + composition root (container)
  ports/               # Protocols for LLM/RAG/cache/security
  adapters/            # LLM (OpenAI-compatible), Chroma, cache, webhooks
  domain/              # Conversation, SenseiConfig, exceptions
  core/                # settings, auth, metrics, rate limit
static/                # tester UI
tests/                 # pytest + tests/live HTTP suite
schemas/               # OpenAPI / SenseiConfig JSON Schema
AGENTS.md              # short do/don’t for contributors & agents
```

## Quick start

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Ollama (lokalnie):
ollama pull qwen2.5-coder:7b
ollama serve
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Domyślnie LLM to lokalne **Ollama** (`LLM_BASE_URL=http://127.0.0.1:11434/v1`, `MAIN_MODEL=qwen2.5-coder:7b`). Alternatywa: LM Studio (`:1234`) — patrz [`.env.example`](.env.example). Po zmianie `.env` **zrestartuj uvicorn**.

`TELEMETRY_URL` domyślnie puste (webhook wyłączony). Log `Telemetry POST … :8080 … 404` oznacza brak odbiorcy Springa — **nie** jest błędem czatu; ustaw URL platformy albo zostaw puste.

### Docker / ekspozycja sieci

Domyślny lokalny start używa `--host 127.0.0.1`. W [`docker-compose.yml`](docker-compose.yml) serwis mapuje port **8000** na hosta z `AI_AUTH_ENABLED=false` — **nie** wystawiaj tego na LAN/chmurę bez auth i `SECURITY_FAIL_CLOSED=true`. Do labów trzymaj bind lokalny lub włącz JWT.

`TRUST_X_FORWARDED_FOR` domyślnie `false` (ignoruje `X-Forwarded-For`, żeby nie dało się ominąć rate limitu). Włącz tylko za zaufanym reverse proxy.

## Docs (PL)

| Dokument | Treść |
|----------|--------|
| [Architektura](docs/ARCHITECTURE.md) | Warstwy, happy-path, bramki, sesje |
| [API](docs/API.md) | Endpointy + przykłady payloadów |
| [Mapa kodu](docs/CODEMAP.md) | Pakiety (bez per-file) |
| [Testy](docs/TESTING.md) | Offline + live S1–S9 (happy/struggle/cheat/edges) |
| [Contributing](CONTRIBUTING.md) | Setup, OpenAPI, PR |
| [AGENTS.md](AGENTS.md) | Krótkie do/don’t |

- Tester UI: http://127.0.0.1:8000/ (**Frontend** — Wykładowca / Student; zwijany **Ops (dev)** u Studenta)
- Scenariusze (log per odpowiedź): http://127.0.0.1:8000/scenarios
- Swagger: http://127.0.0.1:8000/docs
- Health: `GET /health`
- Metrics: `GET /metrics` or `GET /metrics/prometheus`

## Docker Compose

Najpierw `copy .env.example .env`. Przy Ollamie na hoście Windows/Mac ustaw
`LLM_BASE_URL=http://host.docker.internal:11434/v1` (compose ładuje `env_file: .env`).

```bash
docker compose up --build
```

## Tests

Offline (ASGI, bez żywego LLM) — 4 warstwy narracyjne: happy path, struggle, cheat, edges.

Live HTTP (needs `uvicorn` on `:8000` + lokalne Ollama): scenariusze **S1–S9** (`tests/live/scenarios/` + tagi `happy|struggle|cheat|edges`).

```bash
# Full evaluation: offline pytest, then live S1–S9 if API is up (else SKIP live)
.\.venv\Scripts\python.exe -m tests.live.test_all

# Offline only
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m tests.live.test_all --offline-only

# Live subset / groups / require live
.\.venv\Scripts\python.exe -m tests.live.test_scenarios --only 1,4
.\.venv\Scripts\python.exe -m tests.live.test_scenarios --group happy,cheat
.\.venv\Scripts\python.exe -m tests.live.test_all --require-live
```

## API surface

**Happy-path:** `POST /conversations` → optional pre-lab → `messages` / `messages/stream` → `events` / `feedback` → `summary` or `DELETE`.

**Also first-class:** `GET …/restrictions`, `GET …/export`, `GET …/checkpoints`, `POST …/hints/reveal` (after sustained low scores / frustration; session quota), `POST /validate-config`.

**Ops (public):** `GET /health`, `GET /metrics`, `GET /metrics/prometheus`, `GET /` (tester UI).

Pełna mapa + usunięte w slim: [docs/API.md](docs/API.md).

## Notable env flags

| Variable | Default | Meaning |
|----------|---------|---------|
| `LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible API (Ollama / LM Studio) |
| `LLM_API_KEY` | `ollama` | Wymagane przez SDK; lokalnie nie jest sekretem |
| `MAIN_MODEL` / `SECURITY_MODEL` | `qwen2.5-coder:7b` | Modele czatu / security gate |
| `MAIN_MODEL_FALLBACK` | *(puste)* | Opcjonalny model po 429 dostawcy |
| `AI_AUTH_ENABLED` | `false` | Require Bearer JWT |
| `SECURITY_FAIL_CLOSED` | `false` | Block chat if security LLM fails |
| `RATE_LIMIT_PER_MINUTE` | `30` | Sliding window on protected routes |
| `MAX_CONVERSATIONS` / `CONVERSATION_TTL_SECONDS` | `200` / `7200` | In-memory session limits |

Pełna lista z komentarzami: [`.env.example`](.env.example).  
Przykłady payloadów: [docs/API.md](docs/API.md)#przyklady.

## OpenAPI snapshots

Po zmianie routerów / schematów:

```bash
.\.venv\Scripts\python.exe -m scripts.export_openapi
```

Zapisuje `schemas/openapi.json` i `schemas/openapi.yaml`.