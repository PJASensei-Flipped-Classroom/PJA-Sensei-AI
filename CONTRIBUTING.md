# Contributing — PJA-Sensei AI Module

## Setup

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Ustaw lokalne **Ollama** (lub LM Studio) w `.env` — wzór: [`.env.example`](.env.example).  
Domyślnie `LLM_BASE_URL=http://127.0.0.1:11434/v1`, `MAIN_MODEL=qwen2.5-coder:7b`, `LLM_API_KEY=ollama`.  
**Nie commituj** `.env` (jest w `.gitignore`).
Uruchomienie lokalne:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Testy

Szczegóły, tagi live i edge case’y: [docs/TESTING.md](docs/TESTING.md).

| Polecenie | Co robi |
|-----------|---------|
| `python -m pytest -q` | Offline ASGI + unit (bez żywego LLM; `tests/live` wykluczone przez `pytest.ini`) |
| `python -m tests.live.test_all --offline-only` | Orchestrator tylko offline |
| `python -m tests.live.test_all` | Offline, potem live S1–S33 jeśli API na `:8000` |
| `python -m tests.live.test_scenarios --only 6,22` | Wybrane numery live |
| `python -m tests.live.test_scenarios --group student,gates` | Live wg tagów |

Live wymaga działającego `uvicorn` + lokalnego Ollama (lub innego endpointu z `.env`).

## OpenAPI

Po zmianie routerów lub schematów HTTP:

```bash
python -m scripts.export_openapi
```

Commituj zaktualizowane `schemas/openapi.json` i `schemas/openapi.yaml`.

## Debug 403 / rejected message

Kolejność bramek czatu: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — sekcja „Bramki wiadomości”.

## Dokumentacja — co utrzymujemy

- `docs/ARCHITECTURE.md` — warstwy, happy-path, bramki
- `docs/API.md` — endpointy + przykłady payloadów
- `docs/CODEMAP.md` — mapa pakietów (bez per-file)
- `docs/TESTING.md` — offline / live / edges
- **Nie** utrzymujemy `docs/catalog` ani `docs/flows` (katalogi plik-po-pliku)

## Konwencje kodu

1. Kierunek importów i composition root: `AGENTS.md` / `docs/ARCHITECTURE.md`.
2. Use-case’y biorą DTO z `app/application/dto.py`, nie z `app.api`; zależności przez konstruktor (nie `AppContainer`).
3. Routerzy są cienkie: walidacja HTTP + delegacja do `application`; wyjątki domenowe → `errors.py`.
4. camelCase w `SenseiConfig` to kontrakt klienta — bez zmiany bez synchronizacji.
5. OpenAPI: tylko `python -m scripts.export_openapi`.

## Pull request

- Offline `pytest -q` zielone.
- Jeśli zmieniło się API publiczne: odśwież OpenAPI skryptem.
- Krótki opis „dlaczego”, nie tylko „co”.
