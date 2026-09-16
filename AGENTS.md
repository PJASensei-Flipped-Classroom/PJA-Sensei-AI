# AGENTS.md — PJA-Sensei AI Module

Krótkie reguły dla ludzi i agentów Cursor.

## Architecture (do)

- Kierunek importów: `api` → `application` → `ports` / `domain` / `core`.
- Konkretne `adapters` wiruj **tylko** w `AppContainer` (composition root).
- Use-case’y: zależności przez konstruktor — nigdy `AppContainer` w use-case.
- Wspólne DTO request: `app/application/dto.py` (nie `app.api`).
- Wyjątki domenowe w application/domain; HTTP w `app/api/errors.py` (+ cienkie guards).
- DI: `Depends(get_container)` → `request.app.state.container` (lifespan).
- Testy: `create_app(container=AppContainer())` + `TestClient` — bez globalnego kontenera.

## Do not

- Import `app.api` z `application`.
- Drugi singleton kontenera w `deps`.
- Mutacja biznesowa w routerach (np. feedback → `SessionService`).
- Zmiana SenseiConfig **camelCase** bez synchronizacji z klientem IDE.
- Postgres / trwałe sesje bez jawnej decyzji produktowej.

## OpenAPI i testy

- Po zmianie HTTP/schematów: `python -m scripts.export_openapi`
- Offline: `python -m pytest -q`
- Live: uvicorn + Ollama (lub inny URL w `.env`) — `tests/live/`

## Dokumentacja

- Uruchomienie: `docs/URUCHOMIENIE.md`
- Mapa plików: `docs/MAPA_PLIKOW.md`
- Endpointy: `docs/API.md`
- Testy (pliki + komendy): `docs/TESTY.md`
