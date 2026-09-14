# Testy i scenariusze

Mapa pokrycia: **zachowania studenta** (gaming, cheating, edges) oraz kontrakt API.  
API: [API.md](API.md). Live: `tests/live/` (S1–S33, `tests/live/registry.py`).

**Live:** uvicorn + `OPENROUTER_API_KEY`. Po zmianie `.env` zrestartuj serwer.  
Domyślne modele: `:free` (`gemma-4-31b-it` / `lfm` / fallback `nex-n2.5-mini`).

## Komendy

| Polecenie | Co robi |
|-----------|---------|
| `python -m pytest -q` | Offline ASGI + unit (`tests/live` wykluczone przez `pytest.ini`) |
| `python -m tests.live.test_all --offline-only` | Orchestrator tylko offline |
| `python -m tests.live.test_all` | Offline, potem live S1–S33 jeśli API na `:8000` |
| `python -m tests.live.test_scenarios --only 6,22` | Wybrane numery live |
| `python -m tests.live.test_scenarios --group student,gates` | Live wg tagów |
| `python -m tests.live.test_all --require-live` | Fail gdy live niedostępne |

---

## Offline (`python -m pytest -q`)

| Plik | Co pokrywa |
|------|------------|
| `test_student_behavior.py` | Jailbreak, gotowiec, farming reveal, pusty plik, theory, brute-force prelab, `generation_params` |
| `test_api_asgi.py` | Health/metrics, validate-config, lifecycle, prelab gate, idempotency |
| `test_api_edges.py` | 404, file-context, token budget, prelab attempts, soft DELETE, TTL, rate limit, JWT, injection |
| `test_feature_pack.py` | Reveal + quota, next_checkpoint, rich summary, stream webhook, PDF RAG |
| `test_roi_edges.py` | Prelab block chat, reveal sanitize, summary fallback, checkpoint |
| `test_cache_and_security.py` | Cache TTL/LRU, pinned IDs, fail-closed, pedagogy gates |
| `test_code_penalty.py` | `contains_revealed_code` |
| `test_stream_extract.py` | `IncrementalAnswerExtractor` |
| `test_llm_rate_limit.py` | Retry / fallback przy 429 OpenRouter |

Fixtures: `tests/conftest.py` (`AppContainer`, `TestClient`, mock LLM; `client` omija security, `client_secure` nie).

---

## Live S1–S33

Tagi: `pedagogy` | `contract` | `gates` | `roi` | `edge` | **`student`**.  
Pakiety: `scenarios/pedagogy.py` (S1–9), `contract.py` (S10–20, 24), `roi.py` (S21–23, 25–33).  
Helpers: `tests/live/helpers.py`.

| # | Nazwa | Tagi | Co weryfikuje |
|---|-------|------|---------------|
| 1 | Student pyta o teorię bez kodu | pedagogy, student | Tryb teorii → bez gotowca |
| 2 | Student korzysta z materiałów RAG (Spring) | pedagogy, student | Retrieval przy Spring |
| 3 | Student próbuje jailbreak / injection | pedagogy, gates, student | Security bez LLM czatu |
| 4 | Student żąda gotowca (pełny kod) | pedagogy, gates, student | Pedagogy gate |
| 5 | Student frustruje się (niskie score → sokratyzm) | pedagogy, edge, student | Ton frustracji |
| 6 | Student zmienia kod by ominąć cache | pedagogy, student | Cache miss |
| 7 | Student streamuje odpowiedź (JSON escape) | pedagogy, student | NDJSON `answer` |
| 8 | Student wraca do nazw po kompresji historii | pedagogy, student | Pinned identifiers |
| 9 | Awaria RAG nie wywala sesji studenta | pedagogy, edge, student | Degradacja |
| 10 | Health i metrics | contract | `/health`, `/metrics` |
| 11 | GET/DELETE/events/restrictions | contract | Kontrakt sesji / IDE |
| 12 | Student bez zaliczonego pre-lab | contract, gates, student | Chat **403** |
| 13 | Validate config | contract | `POST /validate-config` |
| 14 | Prometheus + request_id | contract | Prometheus + `X-Request-Id` |
| 15 | Export + soft DELETE | contract | Export + soft summary |
| 16 | Live stream tokens | contract | NDJSON + final |
| 17 | Student ponawia client_message_id | contract, student | Idempotency |
| 18 | Student wysyła bogaty CodeContext | contract, student | Kontekst IDE |
| 19 | Student odblokowuje checkpointy / cele | contract, roi, student | Checkpointy + cele |
| 20 | Restrictions endpoint | contract | Flagi IDE / prelab |
| 21 | Student bierze reveal, ocenia, summary | roi, gates, student | Reveal → feedback → summary |
| 22 | Student wyczerpuje budżet tokenów | roi, gates, contract, student | 403 |
| 23 | Student czatuje bez pliku (requireFile) | roi, gates, student | `rejected` |
| 24 | Unknown conversation 404 | contract | 404 |
| 25 | Student farmi reveal niskimi score’ami | roi, edge, student | Streak → reveal |
| 26 | Student wyczerpuje limit reveal | roi, gates, edge, student | Quota → 403 |
| 27 | Student dostaje coaching next_checkpoint | roi, student | Coaching |
| 28 | Rich summary shape | roi | Pola ROI |
| 29 | Student failuje prelab, potem zalicza | roi, gates, student | Fail → pass |
| 30 | Sesja w trybie theory | roi, student | `mode=theory` |
| 31 | PDF RAG material | roi, edge | Ingest PDF |
| 32 | Student generuje eventy IDE → summary | roi, student | Eventy w summary |
| 33 | Sync vs stream parity | roi, contract | Spójny final |

---

## Edge case’y produktowe

| Edge | Zachowanie |
|------|------------|
| Prelab niezaliczony | **403** na chat / reveal |
| Prelab max attempts | Dalsze submit bez zaliczenia; chat **403** |
| Token budget | **403** + opcjonalnie summary w tle |
| Pusty kod + `requireFileContextForChat` | **200** `rejected`; **theory** omija |
| Injection / jailbreak | **200** `blocked` |
| Żądanie pełnego kodu | Pedagogy gate, `penalty_applied` |
| Cache hit | Slim user + assistant; bez LLM |
| Reveal bez streaka | **403** `RevealNotAllowed` |
| Reveal quota | **403** po limicie sesji |
| TTL | Purge przy nowym `POST /conversations`, nie `/health` |
| Rate limit | **429** + `Retry-After` |
| LLM provider 429 | HTTP **200** `message_id: provider_rate_limited`; live SKIP pedagogiki |
| Auth włączony | **401** bez/błędny JWT |
| Soft DELETE | Summary jeśli brak, potem cleanup RAG |
| Stream cancel | Telemetria best-effort |
| Health degraded | **503** (brak klucza / chroma); `/healthz` OK |
| Obcięcie mid-sentence | `max_tokens` theory 700 / debug 900 / review 1000 |

---

## Ograniczenia

Sesje w RAM; config przy imporcie; `MAX_REVEALS_PER_SESSION` hardcode; anty-kod heurystyczny.  
Przy 429 OpenRouter czat wraca HTTP 200 ze stubem (`message_id: provider_rate_limited`). Live S1/S2/S5–S7/S9/S16/S18/S22/S25–S27/S30/S31/S33 wtedy **SKIP** (nie FAIL pedagogiki i nie fałszywy PASS). Bramki bez LLM (S3, S4, kontrakt) nadal się oceniają.  
Gotowe do IDE / Flipped Classroom przy jednym procesie + OpenRouter.
