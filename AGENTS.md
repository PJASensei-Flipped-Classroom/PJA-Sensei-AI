# AGENTS.md — PJA-Sensei AI Module

Short rules for humans and coding agents working in this repo.

## Architecture (do)

- Keep import direction: `api` → `application` → `ports` / `domain` / `core`.
- Wire concrete `adapters` **only** in `AppContainer` (composition root).
- Inject ports/services via constructors — never pass `AppContainer` into use-cases.
- Put shared request DTOs in `app/application/dto.py` (not `app.api`).
- Raise domain exceptions in application/domain; map HTTP in `app/api/errors.py` (+ thin guards).
- Resolve DI with `Depends(get_container)` → `request.app.state.container` (set in lifespan).
- Tests: `create_app(container=AppContainer())` + `TestClient` — no global container.

## Do not

- Import `app.api` from `application`.
- Teach a second container source (`deps` module singleton).
- Put business mutation in routers (e.g. feedback → `SessionService`).
- Change SenseiConfig **camelCase** without syncing the IDE client.
- Revive line-by-line file catalogs under `docs/catalog` or `docs/flows`.
- Add Postgres / durable sessions here without an explicit product decision.

## OpenAPI & tests

- After HTTP/schema changes: `python -m scripts.export_openapi`
- Offline: `python -m pytest -q`
- Live scenarios need uvicorn + OpenRouter (`tests/live/`).

## More detail

- Layers & happy-path: `docs/ARCHITECTURE.md`
- Endpoints & examples: `docs/API.md`
- Package map: `docs/CODEMAP.md`
- Tests / scenarios / edges: `docs/TESTING.md`
- Setup / PR checklist: `CONTRIBUTING.md`
