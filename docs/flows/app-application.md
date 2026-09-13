# Przebiegi: app/ — application

Przypadki użycia: orkiestracja czatu, sesji, prelab, stream, review, summary, goals, analytics.

### `app/application/__init__.py`

- **Rola:** Docstring pakietu use-case'ów.
- **Przebieg funkcjonalności:**
  1. Marker pakietu bez eksportów.

### `app/application/container.py`

- **Rola:** Kontener DI łączący adaptery i serwisy aplikacyjne.
- **Przebieg funkcjonalności:**
  1. `AppContainer.__init__` tworzy llm/client, dict conversations, rag, cache, security.
  2. Następnie sesje, chat, stream, prelab, goals, review, summary, analytics — każdy dostaje `self`.
  3. Żywotność: jeden kontener na proces (lifespan / `init_container`).
- **Główne zależności:** adapters + application services + domain.Conversation

### `app/application/chat.py`

- **Rola:** Serwis czatu: prepare context, cache, send / regenerate / reveal hint.
- **Przebieg funkcjonalności:**
  1. `_prepare_chat_context`: RAG, diff kodu, format CodeContext, opcjonalny append user, kompresja historii, system prompt + pinned note.
  2. `_try_cache` / `_save_cache` / `_track_result_metrics` — exact-match cache (wyłączony przy frustracji) i metryki.
  3. `remember_goal_progress` aktualizuje cele i odblokowuje checkpointy.
  4. `send_message`: bramki prelab/budget → idempotency → cache → LLM JSON → `process_model_response` → cache/idempotency.
  5. `regenerate_message`: usuwa assistant+score, przebudowuje request, LLM z wyższą temperaturą.
  6. `reveal_hint`: tylko przy frustracji/low streak; LLM hint JSON; filtr `contains_revealed_code`.
- **Główne zależności:** sessions, rag, cache, prompts, response_pipeline, metrics

### `app/application/response_pipeline.py`

- **Rola:** Pipeline odpowiedzi: parsing JSON, kary za kod, kompresja historii, streaming extract.
- **Przebieg funkcjonalności:**
  1. `IncrementalAnswerExtractor` dekoduje partial pole `answer` ze strumienia JSON.
  2. `contains_revealed_code` / `code_reveal_fallback` — heurystyka fence/impl vs pedagogika.
  3. `parse_model_json` + `apply_code_penalty` + `process_model_response` — zapis do Conversation, scores, tokens, debug_info.
  4. `llm_error_fallback`, `collect_identifier_tokens`, `format_pinned_identifiers_note`, `compress_history`.
- **Główne zależności:** domain.Conversation

### `app/application/sessions.py`

- **Rola:** Zarządzanie sesjami: TTL, cap, state, export, idempotency, delete + soft summary.
- **Przebieg funkcjonalności:**
  1. `purge_stale_conversations` / `_enforce_conversation_cap` — usuwa RAG + dict.
  2. `start_conversation` tworzy Conversation (prelab_passed zależnie od config).
  3. Bramki: `ensure_prelab_passed`, `ensure_token_budget`, `get_conversation_or_404`.
  4. Odczyty: session state, message history (wyciąga pytanie studenta), restrictions, checkpoints, export.
  5. `record_ide_event`, `lookup/store_idempotent`, `delete_conversation` (opcjonalne summary).
- **Główne zależności:** container conversations/rag/summary, config TTL/MAX

### `app/application/prompts.py`

- **Rola:** Budowa system promptu, formatowanie kontekstu kodu, parametry generacji per mode.
- **Przebieg funkcjonalności:**
  1. `_mode_block` / `generation_params` — theory/debug/review (temperature, max_tokens).
  2. `format_code_context_block` — plik, kod, selection, diagnostics, open files, logi.
  3. `build_system_prompt` — persona, strictRules, cele, frustracja, język, tryb.
- **Główne zależności:** domain.conversation / sensei

### `app/application/stream.py`

- **Rola:** Streaming NDJSON tokenów `answer` + finalny payload.
- **Przebieg funkcjonalności:**
  1. Te same bramki/idempotency/cache co chat; przy hit — fake stream chunkami.
  2. Stream LLM z `IncrementalAnswerExtractor` → eventy `{type:token}`; fallback bez stream_options.
  3. Po strumieniu: `process_model_response`, goal progress, cache, idempotency, `{type:final}`.
- **Główne zależności:** ChatService, response_pipeline, llm client

### `app/application/prelab.py`

- **Rola:** Quiz pre-lab: odczyt publiczny, submit po keywords, generowanie pytań LLM.
- **Przebieg funkcjonalności:**
  1. `get_prelab_public` — pytania bez expected_keywords + stan attempts/score.
  2. `submit_prelab` — limit attempts, matching keywords (lub non-empty), score, passed.
  3. `generate_prelab` — LLM 3 pytania z RAG/materiałów → ustawia `PreLabConfig(enabled=True)`.
- **Główne zależności:** sessions, rag, llm

### `app/application/review.py`

- **Rola:** Sokratyczny review kodu bez pełnych patchy.
- **Przebieg funkcjonalności:**
  1. Bramka prelab; prompt JSON findings + suggested_next_step.
  2. Filtruje messages z `contains_revealed_code`; touch conversation.
- **Główne zależności:** prompts, response_pipeline, llm

### `app/application/summary.py`

- **Rola:** Podsumowanie sesji dla wykładowcy (LLM JSON).
- **Przebieg funkcjonalności:**
  1. Składa historię, scores, feedbacki, IDE events, kryteria ewaluacji.
  2. LLM → mastery_score, student_actions, oceny, professors_summary.
  3. Ustawia `summary_generated` i `last_summary` (+ ide_events w wyniku).
- **Główne zależności:** llm, Conversation

### `app/application/goals.py`

- **Rola:** Ocena postępu celów LLM + powiązanie z checkpointami.
- **Przebieg funkcjonalności:**
  1. `get_checkpoints` deleguje do sessions.
  2. `assess_goals`: prompt z historią → goal_progress; `chat.remember_goal_progress`.
- **Główne zależności:** sessions, chat, llm

### `app/application/analytics.py`

- **Rola:** Agregacja korelacji między aktywnymi sesjami (score, rating, kary, IDE).
- **Przebieg funkcjonalności:**
  1. Purge stale; per-conversation wiersz metryk.
  2. Zwraca listę + globals (avg prompt score / student rating).
- **Główne zależności:** sessions, conversations dict
