# Przebiegi: app/ — adapters

Adaptery I/O: LLM, RAG/Chroma, cache, security gate, webhooki outbound.

### `app/adapters/__init__.py`

- **Rola:** Docstring pakietu adapterów zewnętrznych.
- **Przebieg funkcjonalności:**
  1. Brak logiki — marker pakietu.

### `app/adapters/llm_openrouter.py`

- **Rola:** Klient AsyncOpenAI pod OpenRouter oraz estymacja tokenów.
- **Przebieg funkcjonalności:**
  1. `OpenRouterClient` tworzy `AsyncOpenAI` z base_url i kluczem z config.
  2. `model_for(conversation)` — model z agentBehavior lub `MAIN_MODEL`.
  3. `tokens_from_usage` — total_tokens / prompt+completion / fallback chars//4.
- **Główne zależności:** openai, app.core.config

### `app/adapters/cache_memory.py`

- **Rola:** Cache dokładnego dopasowania odpowiedzi (TTL + LRU).
- **Przebieg funkcjonalności:**
  1. Klucz MD5 z conversation_id + question + error_logs + current_code.
  2. `get_cached_response` — None przy miss/TTL; move_to_end; zwraca kopię dict.
  3. `save_to_cache` — eviction najstarszego przy max_entries; zapisuje timestamp + payload.
  4. Property `size` usuwa expired i zwraca liczbę wpisów.
- **Główne zależności:** app.core.config (CACHE_*)

### `app/adapters/security.py`

- **Rola:** Brama bezpieczeństwa promptów: regex + model security; odpowiedzi blokujące.
- **Przebieg funkcjonalności:**
  1. `get_blocked_response(language)` — gotowy payload MessageResponse (PL/EN) z penalty.
  2. `is_prompt_safe`: najpierw forbidden regex (injection / „daj cały kod” / roleplay).
  3. Potem LLM SECURITY_MODEL z werdyktem SAFE/DANGER.
  4. Przy wyjątku LLM: bezpieczny jeśli nie `SECURITY_FAIL_CLOSED`.
- **Główne zależności:** AsyncOpenAI, app.core.config

### `app/adapters/webhooks.py`

- **Rola:** Wysyłka outbound webhooków telemetry/summary przez httpx.
- **Przebieg funkcjonalności:**
  1. `send_telemetry_webhook(payload, url=None, request_id=…)` dokłada request_id.
  2. POST JSON timeout 2s; log info statusu lub warning przy błędzie (nie rzuca).
- **Główne zależności:** httpx, TELEMETRY_URL

### `app/adapters/rag_chroma.py`

- **Rola:** RAG na ChromaDB: ładowanie HTML, cytacje pdf/slide/video, retrieval.
- **Przebieg funkcjonalności:**
  1. Kolekcja per conversation (`pja_kb_{id}` bez myślników).
  2. `load_materials`: czyści stare dane; doc HTTP → BeautifulSoup → chunk → add; pdf/slide/video tylko metadata cytacji.
  3. `retrieve_context`: cytacje + query top-3; buduje nagłówek PL/EN + fragmenty.
  4. `delete_conversation_data` / `chroma_ok` (heartbeat lub list_collections).
- **Główne zależności:** chromadb, httpx, BeautifulSoup
