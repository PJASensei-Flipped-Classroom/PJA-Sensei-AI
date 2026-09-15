# Mapa kodu (pakiety)

Krótki przegląd odpowiedzialności **pakietów** — bez katalogu plik-po-pliku.  
Warstwy: [ARCHITECTURE.md](ARCHITECTURE.md). API: [API.md](API.md). Testy: [TESTING.md](TESTING.md).

| Pakiet / ścieżka | Odpowiedzialność |
|------------------|------------------|
| `app/main.py` | `create_app()`: lifespan (`app.state.container`), CORS, middleware, routery |
| `app/core` | Settings/env, JWT, metryki, rate limit (stałe zamrożone przy imporcie) |
| `app/domain` | `SenseiConfig` / `Conversation` / wyjątki domenowe (bez FastAPI/LLM) |
| `app/ports` | Protocoly: LLM, RAG, cache, security, summary, ConversationRepository |
| `app/adapters` | LLM (OpenAI-compatible / Ollama), Chroma, cache RAM, security (jailbreak), webhooki, sesje RAM |
| `app/application` | Use-case’y (sessions, chat, stream, prelab, summary), `dto`, `AppContainer`, pedagogy gates, prompts, response pipeline |
| `app/api` | Cienkie routery, deps/guards, schematy HTTP, telemetry helper, mapowanie błędów |
| `static/` | Lokalny tester UI (Wykładowca / Student + Ops) |
| `scripts/` | `python -m scripts.export_openapi` |
| `schemas/` | SenseiConfig JSON Schema + snapshot OpenAPI |
| `tests/` | Offline: happy/struggle/cheat/edges; `tests/live/` S1–S9 |

### Ważne rozróżnienia

- **Security** (`adapters/security`) = jailbreak / injection.  
- **Pedagogy** (`application/pedagogy_gates`) = odmowa gotowca / recall pinned IDs.
- Webhooki wołane z routerów (BackgroundTasks), nie przez `AppContainer`.
- SenseiConfig: **camelCase** (IDE); `Checkpoint` / `CodeContext`: snake_case w kontrakcie.
