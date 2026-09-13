# Przebiegi: tests/

Testy offline (ASGI/unit) oraz suite live HTTP (S1–S24) i orkiestrator ewaluacji.

### `tests/__init__.py`

- **Rola:** Znacznik pakietu testów jednostkowych.
- **Przebieg funkcjonalności:**
  1. Pusty marker.

### `tests/conftest.py`

- **Rola:** Fixtury pytest: TestClient, factory config, mock LLM.
- **Przebieg funkcjonalności:**
  1. `build_valid_config` — minimalny SenseiConfig.
  2. `client` — always-safe security + czysty state; `client_secure` bez bypassu.
  3. `mock_llm_json` stubuje `chat.completions.create` odpowiedzią JSON.
- **Główne zależności:** app.main, deps, SecurityService

### `tests/test_api_asgi.py`

- **Rola:** Testy ASGI happy-path i bramek (offline, bez OpenRouter).
- **Przebieg funkcjonalności:**
  1. Health/metrics, validate-config, lifecycle+events.
  2. Prelab gate block/unlock; idempotency client_message_id.

### `tests/test_api_edges.py`

- **Rola:** Testy krawędziowe API: auth, rate limit, budget, file-context, TTL, soft delete.
- **Przebieg funkcjonalności:**
  1. 404 unknown; walidacja payloadów; requireFileContext.
  2. Token budget 403; prelab max_attempts; soft delete przy fail summary.
  3. TTL purge na health; rate 429; JWT reject; injection regex bez LLM.

### `tests/test_cache_and_security.py`

- **Rola:** Cache TTL/eviction, frustracja, pinne identyfikatory, fail-closed security.
- **Przebieg funkcjonalności:**
  1. Unit ExactMatchCache; helpery frustracji; pinned extraction.
  2. SECURITY_FAIL_CLOSED i regex block przed LLM.

### `tests/test_code_penalty.py`

- **Rola:** Parametryzowane testy heurystyki `contains_revealed_code`.
- **Przebieg funkcjonalności:**
  1. Przepuszcza wskazówki pedagogiczne; blokuje implementacje fence/impl.

### `tests/test_stream_extract.py`

- **Rola:** Testy `IncrementalAnswerExtractor` dla strumienia JSON.
- **Przebieg funkcjonalności:**
  1. Chunki live, pierwsze pole answer, oczekiwanie na niekompletny \u escape.

### `tests/live/__init__.py`

- **Rola:** Znacznik pakietu suite live HTTP.
- **Przebieg funkcjonalności:**
  1. Pusty marker.

### `tests/live/test_all.py`

- **Rola:** Orkiestrator ewaluacji: offline pytest + live S1–S24.
- **Przebieg funkcjonalności:**
  1. CLI: --offline-only / --require-live / --only.
  2. Uruchamia pytest, potem scenariusze live jeśli API dostępne (inaczej SKIP).
  3. Agreguje wyniki BlockResult / podsumowanie.

### `tests/live/test_memory.py`

- **Rola:** Scenariusze live S1–S24 przeciw działającemu serwerowi (:8000 + LLM).
- **Przebieg funkcjonalności:**
  1. HTTP client do real API: theory, RAG, injection, cache, stream, memory, prelab, review, reveal, budget, file-context, 404, …
  2. Filtrowanie `--only`; wynik ScenarioResult per scenariusz.
