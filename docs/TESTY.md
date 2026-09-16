# Testy

Co robi każdy plik testowy i jak uruchomić testy — **każda komenda osobno**.

Aktywuj venv przed wszystkim:

```powershell
.\.venv\Scripts\activate
```

Unix: `source .venv/bin/activate`

---

## Dwa poziomy

| Poziom | LLM | Wymaga uvicorn? | Gdzie |
|--------|-----|-----------------|--------|
| **Offline** | mock | nie | `tests/test_0*.py` (`pytest`; folder `live/` wykluczony) |
| **Live** | prawdziwy (Ollama) | tak, `:8000` | `tests/live/` |

UI z logiem odpowiedzi (nie pytest): http://127.0.0.1:8000/scenarios

---

## Pliki — offline

| Plik | Co robi |
|------|---------|
| [`tests/conftest.py`](../tests/conftest.py) | Fixtures: `AppContainer`, `TestClient` (`client` omija security, `client_secure` nie), `mock_llm_json`, `build_valid_config` |
| [`tests/helpers.py`](../tests/helpers.py) | `start_session`, `msg_body`, `pass_prelab`, `happy_lab_config`, asercje kształtu odpowiedzi |
| [`tests/test_01_happy_path.py`](../tests/test_01_happy_path.py) | Student zalicza lab: health → validate → start → prelab fail+pass → kilka tur czatu → **cel labu 10/10** → summary → export → delete |
| [`tests/test_02_struggle.py`](../tests/test_02_struggle.py) | Utknięcie: reveal po niskich score, quota reveal, `next_checkpoint`, theory vs debug + `requireFileContext` |
| [`tests/test_03_cheat.py`](../tests/test_03_cheat.py) | Oszustwa: jailbreak → `blocked`, gotowiec, farming reveal, brute prelab, pusty plik → `rejected` |
| [`tests/test_04_edges.py`](../tests/test_04_edges.py) | Edges: 404, idempotency, 429 HTTP, JWT 401, budżet PL/EN, TTL, soft DELETE, config fail-closed, stream extractor, LLM 429, RAG SSRF, cyrylica, cache |

---

## Pliki — live

| Plik | Co robi |
|------|---------|
| [`tests/live/helpers.py`](../tests/live/helpers.py) | `API_BASE`, `base_config`, `msg_body`, `start_conversation`, `print_turn`, SKIP przy provider 429 |
| [`tests/live/registry.py`](../tests/live/registry.py) | Rejestr S1–S9 + tagi `happy\|struggle\|cheat\|edges`; filtry `--only` / `--group` |
| [`tests/live/scenarios/happy.py`](../tests/live/scenarios/happy.py) | **S1** — pełny lab do celu 10/10 |
| [`tests/live/scenarios/struggle.py`](../tests/live/scenarios/struggle.py) | **S2** reveal; **S3** theory bez pliku |
| [`tests/live/scenarios/cheat.py`](../tests/live/scenarios/cheat.py) | **S4** jailbreak; **S5** gotowiec; **S6** prelab blokuje chat |
| [`tests/live/scenarios/edges.py`](../tests/live/scenarios/edges.py) | **S7** health+validate; **S8** 404; **S9** token budget |
| [`tests/live/test_scenarios.py`](../tests/live/test_scenarios.py) | Runner HTTP tylko live |
| [`tests/live/test_all.py`](../tests/live/test_all.py) | Orchestrator: najpierw pytest offline, potem live (jeśli API wstało) |

### Live S1–S9 (skrót)

| # | Tag | Tytuł |
|---|-----|--------|
| S1 | happy | Lab od startu do **10/10** |
| S2 | struggle | Reveal po utknięciu |
| S3 | struggle | Theory bez pliku |
| S4 | cheat | Jailbreak |
| S5 | cheat | Gotowiec |
| S6 | cheat / edges | Chat bez prelab → 403 |
| S7 | edges | Health + validate-config |
| S8 | edges | Unknown conversation 404 |
| S9 | edges | Token budget 403 |

---

## Komendy — offline

Cała paczka offline:

```powershell
python -m pytest -q
```

Tylko happy path:

```powershell
python -m pytest -q tests/test_01_happy_path.py
```

Tylko struggle:

```powershell
python -m pytest -q tests/test_02_struggle.py
```

Tylko cheat:

```powershell
python -m pytest -q tests/test_03_cheat.py
```

Tylko edges:

```powershell
python -m pytest -q tests/test_04_edges.py
```

Jeden test po nazwie:

```powershell
python -m pytest -q tests/test_01_happy_path.py::test_student_completes_full_lab_session
```

Verbose (więcej logu):

```powershell
python -m pytest -vv tests/test_03_cheat.py
```

---

## Komendy — live (wymaga API + Ollama)

Terminal 1 — model:

```powershell
ollama serve
```

Terminal 2 — API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Wszystkie live S1–S9:

```powershell
python -m tests.live.test_scenarios
```

Tylko wybrane numery:

```powershell
python -m tests.live.test_scenarios --only 1
```

```powershell
python -m tests.live.test_scenarios --only 1,4,7
```

Tylko warstwa (tag):

```powershell
python -m tests.live.test_scenarios --group happy
```

```powershell
python -m tests.live.test_scenarios --group struggle
```

```powershell
python -m tests.live.test_scenarios --group cheat
```

```powershell
python -m tests.live.test_scenarios --group edges
```

Kilka warstw naraz:

```powershell
python -m tests.live.test_scenarios --group happy,cheat
```

---

## Komendy — orchestrator `test_all`

Offline + live (live SKIP, gdy API nie działa):

```powershell
python -m tests.live.test_all
```

Tylko offline (bez próby live):

```powershell
python -m tests.live.test_all --offline-only
```

Wymuś live (fail, gdy API nie wstanie):

```powershell
python -m tests.live.test_all --require-live
```

Orchestrator z filtrem scenariuszy:

```powershell
python -m tests.live.test_all --only 1,2
```

```powershell
python -m tests.live.test_all --group happy
```

---

## UI scenariuszy

Przy działającym uvicorn:

1. Otwórz http://127.0.0.1:8000/scenarios  
2. Uruchom kartę S1…S9 albo „Uruchom widoczne”  
3. Log w karcie pokazuje każdą odpowiedź API (`status`, `answer`, `cel_labu`)

---

## Uwagi

- `pytest.ini` ma `norecursedirs = live` — samo `pytest` **nie** odpala live.
- Provider 429 w live → scenariusz **SKIP** (nie fail pedagogiki).
- S1 PASS wymaga **celu labu 10/10** (wszystkie `goal_progress` = `done`), nie tylko HTTP 200.
