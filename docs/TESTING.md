# Testy i scenariusze

Testy są ułożone **narracyjnie** (ścieżka studenta), nie jako macierz plików po feature’ach.

API: [API.md](API.md). Live: `tests/live/` (S1–S9, warstwy `happy|struggle|cheat|edges`).

**Live:** uvicorn + lokalne **Ollama** (domyślnie) albo inny OpenAI-compatible URL w `.env`. Po zmianie `.env` zrestartuj serwer.

## Komendy

| Polecenie | Co robi |
|-----------|---------|
| `python -m pytest -q` | Offline ASGI (4 warstwy) |
| `python -m tests.live.test_all --offline-only` | Tylko offline przez orchestrator |
| `python -m tests.live.test_all` | Offline, potem live S1–S9 jeśli API na `:8000` |
| `python -m tests.live.test_scenarios --only 1,4` | Wybrane numery live |
| `python -m tests.live.test_scenarios --group happy,cheat` | Live wg warstw |
| `python -m tests.live.test_all --require-live` | Fail gdy live niedostępne |

---

## Offline (`python -m pytest -q`)

| Plik | Warstwa | Co pokrywa |
|------|---------|------------|
| `test_01_happy_path.py` | Happy | Pełna sesja do **celu labu 10/10** (wszystkie `goal_progress=done`), potem summary → delete |
| `test_02_struggle.py` | Struggle | Reveal po niskich score, quota, `next_checkpoint`, theory vs debug + requireFile |
| `test_03_cheat.py` | Cheat | Jailbreak, gotowiec, farming reveal, brute prelab, pusty plik |
| `test_04_edges.py` | Edges | 404/401/429, budżet PL/EN, TTL, soft DELETE, config fail-closed, stream extractor, LLM 429, RAG SSRF, cyrylica, cache |

Wspólne: `tests/conftest.py`, `tests/helpers.py`. Fixture `client` omija security; `client_secure` nie.

---

## Live S1–S9

| # | Warstwa | Tytuł |
|---|---------|--------|
| S1 | happy | Student przechodzi lab do **10/10** (cele done) |
| S2 | struggle | Student utyka i bierze reveal |
| S3 | struggle | Student w theory bez pliku |
| S4 | cheat | Student próbuje jailbreak |
| S5 | cheat | Student żąda gotowca |
| S6 | cheat/edges | Student bez prelab — chat zablokowany |
| S7 | edges | Health + validate-config |
| S8 | edges | Unknown conversation 404 |
| S9 | edges | Token budget 403 |

Tagi filtra: `happy`, `struggle`, `cheat`, `edges`.

**UI runner:** http://127.0.0.1:8000/scenarios — osobna strona: karta na scenariusz + małe okno logu z każdą odpowiedzią API (`status`, `message_id`, skrócony `answer`).

Provider 429 → scenariusz **SKIP** (nie fail pedagogiki).

---

## Bramki (skrót)

| Zachowanie | HTTP / shape |
|------------|--------------|
| Prelab niezaliczony | 403, `message_id: prelab_required` |
| Budżet tokenów | 403, `message_id: token_budget_exceeded` |
| Reveal bez streaku / po quota | 403 |
| Injection | 200, `message_id: blocked` |
| Brak pliku (requireFile, debug) | 200, `message_id: rejected` |
| Rate limit API | 429 |
| Brak JWT (auth on) | 401 |
