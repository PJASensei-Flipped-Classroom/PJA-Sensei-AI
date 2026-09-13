# app/ — application

Opisy linia-po-linii (język: polski). Puste linie pominięte w wypunktowaniu, ale nie zmieniają numeracji `L`.

<a id="app-application-init-py"></a>
## `app/application/__init__.py`
Pakiet przypadków użycia / orkiestracji.

Liczba linii: **1**.

### Opis linia-po-linii

- **L1:** Docstring: Application use-cases and orchestration.

<a id="app-application-container-py"></a>
## `app/application/container.py`
Kontener DI łączący adaptery i serwisy aplikacyjne.

Liczba linii: **34**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L15:** Importy — L3: `from app.adapters.cache_memory import ExactMatchCache`; L4: `from app.adapters.llm_openrouter import OpenRouterClient`; L5: `from app.adapters.rag_chroma import RagService`; L6: `from app.adapters.security import SecurityService`; L7: `from app.application.analytics import AnalyticsService`; L8: `from app.application.chat import ChatService`; L9: `from app.application.goals import GoalsService`; L10: `from app.application.prelab import PrelabService`; L11: `from app.application.review import ReviewService`; L12: `from app.application.sessions import SessionService`; L13: `from app.application.stream import StreamService`; L14: `from app.application.summary import SummaryService`; L15: `from app.domain.conversation import Conversation`.
- **L18:** Definicja klasy `AppContainer`.
- **L19:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L20:** (w `AppContainer`) Przypisanie `self.llm` ← `OpenRouterClient()`.
- **L21:** (w `AppContainer`) Przypisanie `self.client` ← `self.llm.client`.
- **L22:** (w `AppContainer`) Przypisanie `self.conversations: dict[str, Conversation]` ← `{}`.
- **L23:** (w `AppContainer`) Przypisanie `self.rag` ← `RagService()`.
- **L24:** (w `AppContainer`) Przypisanie `self.cache` ← `ExactMatchCache()`.
- **L25:** (w `AppContainer`) Przypisanie `self.security` ← `SecurityService()`.
- **L27:** (w `AppContainer`) Przypisanie `self.sessions` ← `SessionService(self)`.
- **L28:** (w `AppContainer`) Przypisanie `self.chat` ← `ChatService(self)`.
- **L29:** (w `AppContainer`) Przypisanie `self.stream` ← `StreamService(self)`.
- **L30:** (w `AppContainer`) Przypisanie `self.prelab` ← `PrelabService(self)`.
- **L31:** (w `AppContainer`) Przypisanie `self.goals` ← `GoalsService(self)`.
- **L32:** (w `AppContainer`) Przypisanie `self.review` ← `ReviewService(self)`.
- **L33:** (w `AppContainer`) Przypisanie `self.summary` ← `SummaryService(self)`.
- **L34:** (w `AppContainer`) Przypisanie `self.analytics` ← `AnalyticsService(self)`.

<a id="app-application-chat-py"></a>
## `app/application/chat.py`
Serwis czatu: prepare context, cache, send/regenerate/reveal hint.

Liczba linii: **400**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L8:** Importy — L3: `import difflib`; L4: `import json`; L5: `import logging`; L6: `import re`; L7: `import uuid`; L8: `from typing import TYPE_CHECKING`.
- **L10–L10:** Importy — L10: `from openai.types.chat import ChatCompletionMessageParam`.
- **L12–L29:** Importy — L12: `from app.api.schemas.requests import MessageRequest, RevealHintRequest`; L13: `from app.application.prompts import (`; L14: `build_system_prompt,`; L15: `format_code_context_block,`; L16: `generation_params,`; L17: `)`; L18: `from app.application.response_pipeline import (`; L19: `collect_identifier_tokens,`; L20: `contains_revealed_code,`; L21: `compress_history,`; L22: `format_pinned_identifiers_note,`; L23: `llm_error_fallback,`; L24: `process_model_response,`; L25: `)`; L26: `from app.core.metrics import metrics`; L27: `from app.domain.conversation import Conversation, consecutive_low_enough`; L28: `from app.domain.exceptions import RevealNotAllowed`; L29: `from app.domain.sensei import CodeContext`.
- **L31:** Warunek `if` — gdy `TYPE_CHECKING`.
- **L32–L32:** Importy — L32: `from app.application.container import AppContainer`.
- **L34:** Przypisanie `logger` ← `logging.getLogger(__name__)`.
- **L37:** Definicja klasy `ChatService`.
- **L38:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L39:** (w `ChatService`) Przypisanie `self._app` ← `app`.
- **L41–L47:** (w `ChatService`) Wyrażenie wieloliniowe — L41: Definicja funkcji/metody `?`. | L42: Element listy/argumentów: `self,`. | L43: Element listy/argumentów: `conversation_id: str,`. | L44: Element listy/argumentów: `request: MessageRequest,`. | L45: Element listy/argumentów: `*,`. | L46: Przypisanie `append_user: bool` ← `True,`. | L47: Wykonuje: `) -> tuple[list[ChatCompletionMessageParam], bool, list[dict]]:`.
- **L48:** (w `ChatService`) Przypisanie `conversation` ← `self._app.conversations[conversation_id]`.
- **L49:** (w `ChatService`) Przypisanie `lang` ← `conversation.config.language`.
- **L50:** (w `ChatService`) Wykonuje: `conversation.touch()`.
- **L52–L54:** (w `ChatService`) Wyrażenie wieloliniowe — L52: Przypisanie `rag_context, sources` ← `self._app.rag.retrieve_context(`. | L53: Wykonuje: `conversation_id, request.question`. | L54: Zamknięcie wyrażenia (`)`).
- **L55:** (w `ChatService`) Przypisanie `code_diff_text` ← `""`.
- **L56:** (w `ChatService`) Przypisanie `code_changed` ← `False`.
- **L58:** (w `ChatService`) Warunek `if` — gdy `conversation.last_code and conversation.last_code != request.code_context.current_code`.
- **L59:** (w `ChatService`) Przypisanie `code_changed` ← `True`.
- **L60–L66:** (w `ChatService`) Wyrażenie wieloliniowe — L60: Przypisanie `diff` ← `"\n".join(`. | L61: Wykonuje: `difflib.unified_diff(`. | L62: Element listy/argumentów: `conversation.last_code.splitlines(),`. | L63: Element listy/argumentów: `request.code_context.current_code.splitlines(),`. | L64: Przypisanie `lineterm` ← `"",`. | L65: Zamknięcie wyrażenia (`)`). | L66: Zamknięcie wyrażenia (`)`).
- **L67–L71:** (w `ChatService`) Wyrażenie wieloliniowe — L67: Przypisanie `code_diff_text` ← `(`. | L68: Wykonuje: `f"\nChanges made by student since last prompt:\n```diff\n{diff}\n```\n"`. | L69: Warunek `if` — gdy `lang == "en"`. | L70: Wykonuje: `else f"\nZmiany w kodzie wprowadzone przez studenta od ostatniej porady:\n```diff\n{diff}\n```\n"`. | L71: Zamknięcie wyrażenia (`)`).
- **L73:** (w `ChatService`) Przypisanie `conversation.last_code` ← `request.code_context.current_code`.
- **L75:** (w `ChatService`) Przypisanie `context_block` ← `format_code_context_block(request.code_context, language=lang)`.
- **L76:** (w `ChatService`) Przypisanie `q_label` ← `"Student question" if lang == "en" else "Pytanie studenta"`.
- **L77–L82:** (w `ChatService`) Wyrażenie wieloliniowe — L77: Przypisanie `user_content` ← `(`. | L78: Wykonuje: `f"{context_block}\n"`. | L79: Wykonuje: `f"{code_diff_text}"`. | L80: Wykonuje: `f"{q_label}: {request.question}\n\n"`. | L81: Wykonuje: `f"{rag_context}"`. | L82: Zamknięcie wyrażenia (`)`).
- **L84:** (w `ChatService`) Warunek `if` — gdy `append_user`.
- **L85:** (w `ChatService`) Wykonuje: `conversation.messages.append({"role": "user", "content": user_content})`.
- **L86–L88:** (w `ChatService`) Wyrażenie wieloliniowe — L86: Wykonuje: `conversation.remember_identifiers(`. | L87: Wykonuje: `collect_identifier_tokens(request.question)`. | L88: Zamknięcie wyrażenia (`)`).
- **L90–L92:** (w `ChatService`) Wyrażenie wieloliniowe — L90: Przypisanie `history_clean` ← `[`. | L91: Wykonuje: `{"role": m["role"], "content": m["content"]} for m in conversation.messages`. | L92: Zamknięcie wyrażenia (`]`).
- **L93:** (w `ChatService`) Przypisanie `history_compressed` ← `compress_history(history_clean, language=lang)`.
- **L94:** (w `ChatService`) Przypisanie `system_prompt` ← `build_system_prompt(conversation)`.
- **L95:** (w `ChatService`) Przypisanie `task_label` ← `"Main assignment:" if lang == "en" else "Zadanie główne:"`.
- **L97–L100:** (w `ChatService`) Wyrażenie wieloliniowe — L97: Przypisanie `chat_messages: list[ChatCompletionMessageParam]` ← `[`. | L98: Element listy/argumentów: `{"role": "system", "content": system_prompt},`. | L99: Element listy/argumentów: `{"role": "system", "content": f"{task_label} {conversation.problem}"},`. | L100: Zamknięcie wyrażenia (`]`).
- **L101–L103:** (w `ChatService`) Wyrażenie wieloliniowe — L101: Przypisanie `pinned_note` ← `format_pinned_identifiers_note(`. | L102: Wykonuje: `conversation.pinned_identifiers, lang`. | L103: Zamknięcie wyrażenia (`)`).
- **L104:** (w `ChatService`) Warunek `if` — gdy `pinned_note`.
- **L105:** (w `ChatService`) Wykonuje: `chat_messages.append({"role": "system", "content": pinned_note})`.
- **L106:** (w `ChatService`) Wykonuje: `chat_messages.extend(history_compressed)`.
- **L107:** (w `ChatService`) Zwraca: `chat_messages, code_changed, sources`.
- **L109–L115:** (w `ChatService`) Wyrażenie wieloliniowe — L109: Definicja funkcji/metody `?`. | L110: Element listy/argumentów: `self,`. | L111: Element listy/argumentów: `conversation: Conversation,`. | L112: Element listy/argumentów: `conversation_id: str,`. | L113: Element listy/argumentów: `request: MessageRequest,`. | L114: Przypisanie `message_id: str | None` ← `None,`. | L115: Wykonuje: `) -> dict | None:`.
- **L116:** (w `ChatService`) Warunek `if` — gdy `conversation.is_frustrated`.
- **L117:** (w `ChatService`) Zwraca: `None`.
- **L119–L124:** (w `ChatService`) Wyrażenie wieloliniowe — L119: Przypisanie `cached` ← `self._app.cache.get_cached_response(`. | L120: Element listy/argumentów: `conversation_id,`. | L121: Element listy/argumentów: `request.question,`. | L122: Element listy/argumentów: `request.code_context.error_logs,`. | L123: Element listy/argumentów: `request.code_context.current_code,`. | L124: Zamknięcie wyrażenia (`)`).
- **L125:** (w `ChatService`) Warunek `if` — gdy `not cached`.
- **L126:** (w `ChatService`) Wykonuje: `metrics.inc("cache_misses")`.
- **L127:** (w `ChatService`) Zwraca: `None`.
- **L129:** (w `ChatService`) Wykonuje: `metrics.inc("cache_hits")`.
- **L130:** (w `ChatService`) Przypisanie `result` ← `dict(cached)`.
- **L131:** (w `ChatService`) Przypisanie `result["is_cached"]` ← `True`.
- **L132:** (w `ChatService`) Warunek `if` — gdy `message_id is not None`.
- **L133:** (w `ChatService`) Przypisanie `result["message_id"]` ← `message_id`.
- **L135:** (w `ChatService`) Wykonuje: `conversation.prompt_scores.append(result["prompt_score"])`.
- **L136:** (w `ChatService`) Przypisanie `conversation.tokens_used_total +` ← `int(result.get("tokens_used") or 0)`.
- **L137:** (w `ChatService`) Wykonuje: `conversation.touch()`.
- **L138–L149:** (w `ChatService`) Wyrażenie wieloliniowe — L138: Wykonuje: `conversation.messages.append(`. | L139: Wykonuje: `{`. | L140: Element listy/argumentów: `"role": "assistant",`. | L141: Element listy/argumentów: `"content": result["answer"],`. | L142: Element listy/argumentów: `"message_id": result["message_id"],`. | L143: Element listy/argumentów: `"penalty_applied": result.get("penalty_applied", False),`. | L144: Element listy/argumentów: `"prompt_score": result.get("prompt_score"),`. | L145: Element listy/argumentów: `"sources": result.get("sources") or [],`. | L146: Element listy/argumentów: `"suggested_next_step": result.get("suggested_next_step"),`. | L147: Element listy/argumentów: `"goal_progress": result.get("goal_progress") or [],`. | L148: Zamknięcie wyrażenia (`}`). | L149: Zamknięcie wyrażenia (`)`).
- **L150:** (w `ChatService`) Przypisanie `debug` ← `dict(result.get("debug_info") or {})`.
- **L151:** (w `ChatService`) Przypisanie `debug["is_frustrated"]` ← `conversation.is_frustrated`.
- **L152:** (w `ChatService`) Przypisanie `result["debug_info"]` ← `debug`.
- **L153:** (w `ChatService`) Zwraca: `result`.
- **L155–L160:** (w `ChatService`) Wyrażenie wieloliniowe — L155: Definicja funkcji/metody `?`. | L156: Element listy/argumentów: `self,`. | L157: Element listy/argumentów: `conversation_id: str,`. | L158: Element listy/argumentów: `request: MessageRequest,`. | L159: Element listy/argumentów: `final_result: dict,`. | L160: Wykonuje: `) -> None:`.
- **L161–L167:** (w `ChatService`) Wyrażenie wieloliniowe — L161: Wykonuje: `self._app.cache.save_to_cache(`. | L162: Element listy/argumentów: `conversation_id,`. | L163: Element listy/argumentów: `request.question,`. | L164: Element listy/argumentów: `request.code_context.error_logs,`. | L165: Element listy/argumentów: `request.code_context.current_code,`. | L166: Element listy/argumentów: `final_result,`. | L167: Zamknięcie wyrażenia (`)`).
- **L169:** Definicja funkcji/metody `_track_result_metrics`, zwraca `None`.
- **L170:** (w `ChatService`) Wykonuje: `metrics.inc("messages_total")`.
- **L171:** (w `ChatService`) Wykonuje: `metrics.inc("tokens_total", int(result.get("tokens_used") or 0))`.
- **L172:** (w `ChatService`) Warunek `if` — gdy `result.get("penalty_applied")`.
- **L173:** (w `ChatService`) Wykonuje: `metrics.inc("penalties_total")`.
- **L175:** Definicja funkcji/metody `remember_goal_progress`, zwraca `None`.
- **L176:** (w `ChatService`) Przypisanie `progress` ← `result.get("goal_progress") or []`.
- **L177:** (w `ChatService`) Warunek `if` — gdy `progress`.
- **L178:** (w `ChatService`) Przypisanie `conversation.goal_progress` ← `list(progress)`.
- **L179:** (w `ChatService`) Przypisanie `done` ← `{g.get("goal") for g in progress if g.get("status") == "done"}`.
- **L180:** (w `ChatService`) Pętla `for` po `cp in conversation.config.checkpoints`.
- **L181:** (w `ChatService`) Warunek `if` — gdy `cp.after_goal in done and cp.id not in conversation.unlocked_checkpoints`.
- **L182:** (w `ChatService`) Wykonuje: `conversation.unlocked_checkpoints.append(cp.id)`.
- **L184:** Definicja funkcji/metody `_gen_kwargs`, zwraca `dict`.
- **L185:** (w `ChatService`) Przypisanie `params` ← `generation_params(conversation.config.agentBehavior.mode or "debug")`.
- **L186–L192:** (w `ChatService`) Wyrażenie wieloliniowe — L186: Zwraca: `{`. | L187: Element listy/argumentów: `"temperature": params["temperature"],`. | L188: Element listy/argumentów: `"presence_penalty": 0.6,`. | L189: Element listy/argumentów: `"frequency_penalty": 0.4,`. | L190: Element listy/argumentów: `"max_tokens": params["max_tokens"],`. | L191: Element listy/argumentów: `"response_format": {"type": "json_object"},`. | L192: Zamknięcie wyrażenia (`}`).
- **L194:** Definicja asynchronicznej funkcji/metody `send_message`, zwraca `dict`.
- **L195:** (w `ChatService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L196:** (w `ChatService`) Wykonuje: `self._app.sessions.ensure_prelab_passed(conversation)`.
- **L197:** (w `ChatService`) Wykonuje: `self._app.sessions.ensure_token_budget(conversation)`.
- **L199–L201:** (w `ChatService`) Wyrażenie wieloliniowe — L199: Przypisanie `prior` ← `self._app.sessions.lookup_idempotent(`. | L200: Wykonuje: `conversation_id, request.client_message_id`. | L201: Zamknięcie wyrażenia (`)`).
- **L202:** (w `ChatService`) Warunek `if` — gdy `prior`.
- **L203:** (w `ChatService`) Wykonuje: `self._track_result_metrics(prior)`.
- **L204:** (w `ChatService`) Zwraca: `prior`.
- **L206:** (w `ChatService`) Przypisanie `was_frustrated` ← `conversation.is_frustrated`.
- **L207:** (w `ChatService`) Przypisanie `cached` ← `self._try_cache(conversation, conversation_id, request)`.
- **L208:** (w `ChatService`) Warunek `if` — gdy `cached`.
- **L209–L211:** (w `ChatService`) Wyrażenie wieloliniowe — L209: Przypisanie `cached` ← `self._app.sessions.store_idempotent(`. | L210: Wykonuje: `conversation_id, request.client_message_id, cached`. | L211: Zamknięcie wyrażenia (`)`).
- **L212:** (w `ChatService`) Wykonuje: `self._track_result_metrics(cached)`.
- **L213:** (w `ChatService`) Zwraca: `cached`.
- **L215–L217:** (w `ChatService`) Wyrażenie wieloliniowe — L215: Przypisanie `chat_messages, code_changed, sources` ← `await self._prepare_chat_context(`. | L216: Wykonuje: `conversation_id, request`. | L217: Zamknięcie wyrażenia (`)`).
- **L219:** (w `ChatService`) Blok `try` — chroniony kod, potem except/finally.
- **L220–L224:** (w `ChatService`) Wyrażenie wieloliniowe — L220: Przypisanie `response` ← `await self._app.client.chat.completions.create(`. | L221: Przypisanie `model` ← `self._app.llm.model_for(conversation),`. | L222: Przypisanie `messages` ← `chat_messages,`. | L223: Element listy/argumentów: `**self._gen_kwargs(conversation),`. | L224: Zamknięcie wyrażenia (`)`).
- **L225:** (w `ChatService`) Przypisanie `raw_content` ← `response.choices[0].message.content or ""`.
- **L226:** (w `ChatService`) Przypisanie `prompt_text` ← `"\n".join(str(m.get("content") or "") for m in chat_messages)`.
- **L227–L229:** (w `ChatService`) Wyrażenie wieloliniowe — L227: Przypisanie `tokens_used` ← `self._app.llm.tokens_from_usage(`. | L228: Wykonuje: `response.usage, prompt_text, raw_content`. | L229: Zamknięcie wyrażenia (`)`).
- **L230:** (w `ChatService`) Przechwytuje wyjątek `Exception as e`.
- **L231:** (w `ChatService`) Wykonuje: `metrics.inc("llm_errors")`.
- **L232:** (w `ChatService`) Log: `logger.error("Error calling LLM API: %s", e)`.
- **L233:** (w `ChatService`) Przypisanie `message_id` ← `str(uuid.uuid4())`.
- **L234:** (w `ChatService`) Zwraca: `llm_error_fallback(message_id, conversation.config.language)`.
- **L236:** (w `ChatService`) Przypisanie `message_id` ← `str(uuid.uuid4())`.
- **L237–L245:** (w `ChatService`) Wyrażenie wieloliniowe — L237: Przypisanie `final_result` ← `process_model_response(`. | L238: Element listy/argumentów: `raw_content,`. | L239: Element listy/argumentów: `conversation,`. | L240: Przypisanie `message_id` ← `message_id,`. | L241: Przypisanie `tokens_used` ← `tokens_used,`. | L242: Przypisanie `code_changed` ← `code_changed,`. | L243: Przypisanie `was_frustrated` ← `was_frustrated,`. | L244: Przypisanie `sources` ← `sources,`. | L245: Zamknięcie wyrażenia (`)`).
- **L246:** (w `ChatService`) Wykonuje: `self.remember_goal_progress(conversation, final_result)`.
- **L247:** (w `ChatService`) Wykonuje: `self._save_cache(conversation_id, request, final_result)`.
- **L248–L250:** (w `ChatService`) Wyrażenie wieloliniowe — L248: Przypisanie `final_result` ← `self._app.sessions.store_idempotent(`. | L249: Wykonuje: `conversation_id, request.client_message_id, final_result`. | L250: Zamknięcie wyrażenia (`)`).
- **L251:** (w `ChatService`) Wykonuje: `self._track_result_metrics(final_result)`.
- **L252:** (w `ChatService`) Zwraca: `final_result`.
- **L254–L256:** (w `ChatService`) Wyrażenie wieloliniowe — L254: Definicja funkcji/metody `?`. | L255: Wykonuje: `self, conversation_id: str, message_id: str`. | L256: Wykonuje: `) -> dict:`.
- **L257:** (w `ChatService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L258:** (w `ChatService`) Wykonuje: `self._app.sessions.ensure_prelab_passed(conversation)`.
- **L259:** (w `ChatService`) Wykonuje: `self._app.sessions.ensure_token_budget(conversation)`.
- **L261–L268:** (w `ChatService`) Wyrażenie wieloliniowe — L261: Przypisanie `idx` ← `next(`. | L262: Wykonuje: `(`. | L263: Wykonuje: `i`. | L264: Pętla `for` po `i, m in enumerate(conversation.messages)`. | L265: Warunek `if` — gdy `m.get("message_id") == message_id and m.get("role") == "assistant"`. | L266: Element listy/argumentów: `),`. | L267: Element listy/argumentów: `None,`. | L268: Zamknięcie wyrażenia (`)`).
- **L269:** (w `ChatService`) Warunek `if` — gdy `idx is None`.
- **L270:** (w `ChatService`) Rzuca wyjątek: `KeyError("message_not_found")`.
- **L271:** (w `ChatService`) Warunek `if` — gdy `idx == 0 or conversation.messages[idx - 1].get("role") != "user"`.
- **L272:** (w `ChatService`) Rzuca wyjątek: `KeyError("user_context_missing")`.
- **L274:** (w `ChatService`) Wykonuje: `conversation.messages.pop(idx)`.
- **L275:** (w `ChatService`) Warunek `if` — gdy `conversation.prompt_scores`.
- **L276:** (w `ChatService`) Wykonuje: `conversation.prompt_scores.pop()`.
- **L278:** (w `ChatService`) Przypisanie `user_content` ← `conversation.messages[idx - 1]["content"]`.
- **L279–L283:** (w `ChatService`) Wyrażenie wieloliniowe — L279: Przypisanie `q_match` ← `re.search(`. | L280: Element listy/argumentów: `r"(?:Student question|Pytanie studenta):\s*(.*)$",`. | L281: Element listy/argumentów: `user_content,`. | L282: Element listy/argumentów: `re.MULTILINE,`. | L283: Zamknięcie wyrażenia (`)`).
- **L284:** (w `ChatService`) Przypisanie `question` ← `q_match.group(1).strip() if q_match else "Please continue."`.
- **L285–L292:** (w `ChatService`) Wyrażenie wieloliniowe — L285: Przypisanie `request` ← `MessageRequest(`. | L286: Przypisanie `question` ← `question,`. | L287: Przypisanie `code_context` ← `CodeContext(`. | L288: Przypisanie `current_file_name` ← `"unknown",`. | L289: Przypisanie `current_code` ← `conversation.last_code,`. | L290: Przypisanie `error_logs` ← `"",`. | L291: Element listy/argumentów: `),`. | L292: Zamknięcie wyrażenia (`)`).
- **L294:** (w `ChatService`) Przypisanie `was_frustrated` ← `conversation.is_frustrated`.
- **L295–L297:** (w `ChatService`) Wyrażenie wieloliniowe — L295: Przypisanie `chat_messages, code_changed, sources` ← `await self._prepare_chat_context(`. | L296: Przypisanie `conversation_id, request, append_user` ← `False`. | L297: Zamknięcie wyrażenia (`)`).
- **L298:** (w `ChatService`) Blok `try` — chroniony kod, potem except/finally.
- **L299:** (w `ChatService`) Przypisanie `gen` ← `self._gen_kwargs(conversation)`.
- **L300–L308:** (w `ChatService`) Wyrażenie wieloliniowe — L300: Przypisanie `response` ← `await self._app.client.chat.completions.create(`. | L301: Przypisanie `model` ← `self._app.llm.model_for(conversation),`. | L302: Przypisanie `messages` ← `chat_messages,`. | L303: Przypisanie `temperature` ← `min(0.9, gen["temperature"] + 0.1),`. | L304: Przypisanie `presence_penalty` ← `gen["presence_penalty"],`. | L305: Przypisanie `frequency_penalty` ← `gen["frequency_penalty"],`. | L306: Przypisanie `max_tokens` ← `gen["max_tokens"],`. | L307: Przypisanie `response_format` ← `gen["response_format"],`. | L308: Zamknięcie wyrażenia (`)`).
- **L309:** (w `ChatService`) Przypisanie `raw_content` ← `response.choices[0].message.content or ""`.
- **L310:** (w `ChatService`) Przypisanie `prompt_text` ← `"\n".join(str(m.get("content") or "") for m in chat_messages)`.
- **L311–L313:** (w `ChatService`) Wyrażenie wieloliniowe — L311: Przypisanie `tokens_used` ← `self._app.llm.tokens_from_usage(`. | L312: Wykonuje: `response.usage, prompt_text, raw_content`. | L313: Zamknięcie wyrażenia (`)`).
- **L314:** (w `ChatService`) Przechwytuje wyjątek `Exception as e`.
- **L315:** (w `ChatService`) Wykonuje: `metrics.inc("llm_errors")`.
- **L316:** (w `ChatService`) Zwraca: `llm_error_fallback(str(uuid.uuid4()), conversation.config.language)`.
- **L318:** (w `ChatService`) Przypisanie `new_id` ← `str(uuid.uuid4())`.
- **L319–L327:** (w `ChatService`) Wyrażenie wieloliniowe — L319: Przypisanie `result` ← `process_model_response(`. | L320: Element listy/argumentów: `raw_content,`. | L321: Element listy/argumentów: `conversation,`. | L322: Przypisanie `message_id` ← `new_id,`. | L323: Przypisanie `tokens_used` ← `tokens_used,`. | L324: Przypisanie `code_changed` ← `code_changed,`. | L325: Przypisanie `was_frustrated` ← `was_frustrated,`. | L326: Przypisanie `sources` ← `sources,`. | L327: Zamknięcie wyrażenia (`)`).
- **L328:** (w `ChatService`) Wykonuje: `self.remember_goal_progress(conversation, result)`.
- **L329:** (w `ChatService`) Wykonuje: `self._track_result_metrics(result)`.
- **L330:** (w `ChatService`) Zwraca: `result`.
- **L332–L334:** (w `ChatService`) Wyrażenie wieloliniowe — L332: Definicja funkcji/metody `?`. | L333: Wykonuje: `self, conversation_id: str, payload: RevealHintRequest`. | L334: Wykonuje: `) -> dict:`.
- **L335:** (w `ChatService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L336:** (w `ChatService`) Wykonuje: `self._app.sessions.ensure_prelab_passed(conversation)`.
- **L337–L340:** (w `ChatService`) Wyrażenie wieloliniowe — L337: Warunek `if` — gdy `not (`. | L338: Wykonuje: `conversation.is_frustrated`. | L339: Wykonuje: `or consecutive_low_enough(conversation.prompt_scores)`. | L340: Wykonuje: `):`.
- **L341–L343:** (w `ChatService`) Wyrażenie wieloliniowe — L341: Rzuca wyjątek: `RevealNotAllowed(`. | L342: Wykonuje: `"Reveal available only after sustained low scores / frustration"`. | L343: Zamknięcie wyrażenia (`)`).
- **L345:** (w `ChatService`) Przypisanie `lang` ← `conversation.config.language`.
- **L346–L350:** (w `ChatService`) Wyrażenie wieloliniowe — L346: Przypisanie `code` ← `(`. | L347: Wykonuje: `payload.code_context.current_code`. | L348: Warunek `if` — gdy `payload.code_context`. | L349: Wykonuje: `else conversation.last_code`. | L350: Zamknięcie wyrażenia (`)`).
- **L351:** (w `ChatService`) Przypisanie `focus` ← `payload.focus or ""`.
- **L352:** (w `ChatService`) Przypisanie `prompt` ← `f"""`.
- **L353:** (w `ChatService`) Wykonuje: `You are a Socratic mentor giving ONE stronger unlocking hint (still NO full solution code).`.
- **L354:** (w `ChatService`) Przypisanie `Language: {"English" if lang` ← `= "en" else "Polish"}.`.
- **L355:** (w `ChatService`) Wykonuje: `Assignment: {conversation.problem}`.
- **L356:** (w `ChatService`) Wykonuje: `Student code:`.
- **L357:** (w `ChatService`) Wykonuje: `{code}`.
- **L358:** (w `ChatService`) Wykonuje: `Focus: {focus}`.
- **L360:** (w `ChatService`) Wykonuje: `Return JSON: {{"hint": "...", "suggested_next_step": "..."}}`.
- **L361–L400:** Docstring / wieloliniowy literał tekstowy (otwarcie w L361, zamknięcie w L400).

<a id="app-application-response-pipeline-py"></a>
## `app/application/response_pipeline.py`
Pipeline odpowiedzi LLM: parsing JSON, kary za kod, kompresja historii, streaming extract.

Liczba linii: **416**.

### Opis linia-po-linii

- **L1–L3:** Importy — L1: `import json`; L2: `import re`; L3: `from typing import Any`.
- **L5–L5:** Importy — L5: `from app.domain.conversation import Conversation, recent_avg_score`.
- **L7–L10:** Wyrażenie wieloliniowe — L7: Przypisanie `DEFAULT_CODE_FALLBACK_PL` ← `(`. | L8: Wykonuje: `"Zauważyłem próbę wygenerowania gotowego kodu, co narusza zasady samodzielnej pracy. "`. | L9: Wykonuje: `"Zastanówmy się nad architekturą rozwiązania: jakich komponentów potrzebujesz?"`. | L10: Zamknięcie wyrażenia (`)`).
- **L12–L15:** Wyrażenie wieloliniowe — L12: Przypisanie `DEFAULT_CODE_FALLBACK_EN` ← `(`. | L13: Wykonuje: `"I noticed an attempt to generate complete code, which violates the self-learning rules. "`. | L14: Wykonuje: `"Let's think about the concept together."`. | L15: Zamknięcie wyrażenia (`)`).
- **L17:** Przypisanie `_CODE_BLOCK_RE` ← `re.compile(r"```([a-zA-Z0-9_-]*)\n(.*?)```", re.DOTALL)`.
- **L19:** Przypisanie `_ANSWER_KEY_RE` ← `re.compile(r'"answer"\s*:\s*"')`.
- **L22:** Definicja klasy `IncrementalAnswerExtractor`.
- **L23:** Docstring: Extract the JSON string value of ``answer`` as it streams in character-by-character.
- **L25:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L26:** (w `IncrementalAnswerExtractor`) Przypisanie `self._raw` ← `""`.
- **L27:** (w `IncrementalAnswerExtractor`) Przypisanie `self._emitted` ← `0`.
- **L29:** Definicja funkcji/metody `feed`, zwraca `str`.
- **L30:** (w `IncrementalAnswerExtractor`) Warunek `if` — gdy `not piece`.
- **L31:** (w `IncrementalAnswerExtractor`) Zwraca: `""`.
- **L32:** (w `IncrementalAnswerExtractor`) Przypisanie `self._raw +` ← `piece`.
- **L33:** (w `IncrementalAnswerExtractor`) Przypisanie `partial` ← `_decode_partial_json_string_field(self._raw)`.
- **L34:** (w `IncrementalAnswerExtractor`) Warunek `if` — gdy `len(partial) <= self._emitted`.
- **L35:** (w `IncrementalAnswerExtractor`) Zwraca: `""`.
- **L36:** (w `IncrementalAnswerExtractor`) Przypisanie `delta` ← `partial[self._emitted :]`.
- **L37:** (w `IncrementalAnswerExtractor`) Przypisanie `self._emitted` ← `len(partial)`.
- **L38:** (w `IncrementalAnswerExtractor`) Zwraca: `delta`.
- **L40:** (w `IncrementalAnswerExtractor`) Dekorator `@property` (np. route FastAPI, fixture, dataclass).
- **L41:** Definicja funkcji/metody `answer_so_far`, zwraca `str`.
- **L42:** (w `IncrementalAnswerExtractor`) Zwraca: `_decode_partial_json_string_field(self._raw)`.
- **L45:** Definicja funkcji/metody `_decode_partial_json_string_field`, zwraca `str`.
- **L46:** Docstring: Return decoded contents of the ``answer`` string seen so far (may be incomplete).
- **L47:** (w `_decode_partial_json_string_field`) Przypisanie `match` ← `_ANSWER_KEY_RE.search(raw)`.
- **L48:** (w `_decode_partial_json_string_field`) Warunek `if` — gdy `not match`.
- **L49:** (w `_decode_partial_json_string_field`) Zwraca: `""`.
- **L50:** (w `_decode_partial_json_string_field`) Przypisanie `i` ← `match.end()`.
- **L51:** (w `_decode_partial_json_string_field`) Przypisanie `out: list[str]` ← `[]`.
- **L52:** (w `_decode_partial_json_string_field`) Pętla `while` dopóki `i < len(raw)`.
- **L53:** (w `_decode_partial_json_string_field`) Przypisanie `ch` ← `raw[i]`.
- **L54:** (w `_decode_partial_json_string_field`) Warunek `if` — gdy `ch == "\\"`.
- **L55:** (w `_decode_partial_json_string_field`) Warunek `if` — gdy `i + 1 >= len(raw)`.
- **L56:** (w `_decode_partial_json_string_field`) Wykonuje: `break # incomplete escape — wait for more bytes`.
- **L57:** (w `_decode_partial_json_string_field`) Przypisanie `nxt` ← `raw[i + 1]`.
- **L58:** (w `_decode_partial_json_string_field`) Przypisanie `simple` ← `{"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}`.
- **L59:** (w `_decode_partial_json_string_field`) Warunek `if` — gdy `nxt in simple`.
- **L60:** (w `_decode_partial_json_string_field`) Wykonuje: `out.append(simple[nxt])`.
- **L61:** (w `_decode_partial_json_string_field`) Przypisanie `i +` ← `2`.
- **L62:** (w `_decode_partial_json_string_field`) Przechodzi do kolejnej iteracji pętli (`continue`).
- **L63:** (w `_decode_partial_json_string_field`) Warunek `if` — gdy `nxt == "u"`.
- **L64:** (w `_decode_partial_json_string_field`) Warunek `if` — gdy `i + 5 >= len(raw)`.
- **L65:** (w `_decode_partial_json_string_field`) Przerywa pętlę (`break`).
- **L66:** (w `_decode_partial_json_string_field`) Przypisanie `hexpart` ← `raw[i + 2 : i + 6]`.
- **L67:** (w `_decode_partial_json_string_field`) Blok `try` — chroniony kod, potem except/finally.
- **L68:** (w `_decode_partial_json_string_field`) Wykonuje: `out.append(chr(int(hexpart, 16)))`.
- **L69:** (w `_decode_partial_json_string_field`) Przypisanie `i +` ← `6`.
- **L70:** (w `_decode_partial_json_string_field`) Przechodzi do kolejnej iteracji pętli (`continue`).
- **L71:** (w `_decode_partial_json_string_field`) Przechwytuje wyjątek `ValueError`.
- **L72:** (w `_decode_partial_json_string_field`) Wykonuje: `out.append(nxt)`.
- **L73:** (w `_decode_partial_json_string_field`) Przypisanie `i +` ← `2`.
- **L74:** (w `_decode_partial_json_string_field`) Przechodzi do kolejnej iteracji pętli (`continue`).
- **L75:** (w `_decode_partial_json_string_field`) Wykonuje: `out.append(nxt)`.
- **L76:** (w `_decode_partial_json_string_field`) Przypisanie `i +` ← `2`.
- **L77:** (w `_decode_partial_json_string_field`) Przechodzi do kolejnej iteracji pętli (`continue`).
- **L78:** (w `_decode_partial_json_string_field`) Warunek `if` — gdy `ch == '"'`.
- **L79:** (w `_decode_partial_json_string_field`) Wykonuje: `break # end of JSON string`.
- **L80:** (w `_decode_partial_json_string_field`) Wykonuje: `out.append(ch)`.
- **L81:** (w `_decode_partial_json_string_field`) Przypisanie `i +` ← `1`.
- **L82:** (w `_decode_partial_json_string_field`) Zwraca: `"".join(out)`.
- **L85–L416:** Wyrażenie wieloliniowe — L85: Przypisanie `_IMPL_BODY_RE` ← `re.compile(`. | L86: Wykonuje: `r"(public\s+class\s+\w+\s*\{[\s\S]{20,})"`. | L87: Wykonuje: `r"|(public\s+(static\s+)?[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{)"`. | L88: Wykonuje: `r"|(def\s+\w+\s*\([^)]*\)\s*:)"`. | L89: Wykonuje: `r"|(return\s+new\s+\w+\s*\()"`. | L90: Komentarz: for/while header may contain nested () e.g. list.size() | L91: Element listy/argumentów: `r"|((?:for|while)\s*\([^\n]*\)\s*\{)",`. | L92: Element listy/argumentów: `re.MULTILINE,`. | L93: Zamknięcie wyrażenia (`)`). | L94:  | L95: Przypisanie `_IMPL_LINE_RE` ← `re.compile(`. | L96: Wykonuje: `r"^\s*(public|private|protected)\s+"`. | L97: Wykonuje: `r"|^\s*def\s+\w+"`. | L98: Wykonuje: `r"|^\s*return\s+"`. | L99: Wykonuje: `r"|^\s*(if|for|while)\s*\("`. | L100: Przypisanie `r"|^\s*\w+\s*` ← `\s*new\s+"`. | L101: Zamknięcie wyrażenia (`)`). | L102:  | L103:  | L104: Definicja funkcji/metody `_fenced_block_is_implementation`, zwraca `bool`. | L105: Warunek `if` — gdy `lang_hint.lower() in ("diff", "text", "plaintext", "md", "markdown", "json")`. | L106: Zwraca: `False`. | L107: Przypisanie `lines` ← `[ln for ln in block_body.splitlines() if ln.strip()]`. | L108: Zwraca: `len(lines) >= 2`. | L109:  | L110:  | L111: Definicja funkcji/metody `contains_revealed_code`, zwraca `bool`. | L112: Docstring: True if the answer looks like a full implementation dump (fenced or raw). | L113: Pętla `for` po `match in _CODE_BLOCK_RE.finditer(answer_text)`. | L114: Przypisanie `lang_hint` ← `match.group(1) or ""`. | L115: Przypisanie `body` ← `match.group(2) or ""`. | L116: Warunek `if` — gdy `_fenced_block_is_implementation(body, lang_hint)`. | L117: Zwraca: `True`. | L118:  | L119: Warunek `if` — gdy `_IMPL_BODY_RE.search(answer_text)`. | L120: Zwraca: `True`. | L121:  | L122: Przypisanie `impl_lines` ← `[`. | L123: Wykonuje: `line`. | L124: Pętla `for` po `line in answer_text.splitlines()`. | L125: Warunek `if` — gdy `_IMPL_LINE_RE.search(line)`. | L126: Zamknięcie wyrażenia (`]`). | L127: Zwraca: `len(impl_lines) >= 3`. | L128:  | L129:  | L130: Definicja funkcji/metody `code_reveal_fallback`, zwraca `str`. | L131: Przypisanie `custom` ← `getattr(conversation.config.agentBehavior, "codeRevealFallback", None)`. | L132: Warunek `if` — gdy `custom`. | L133: Zwraca: `custom`. | L134: Warunek `if` — gdy `conversation.config.language == "pl"`. | L135: Zwraca: `DEFAULT_CODE_FALLBACK_PL`. | L136: Zwraca: `DEFAULT_CODE_FALLBACK_EN`. | L137:  | L138:  | L139: Definicja funkcji/metody `_safe_decode_json_string`, zwraca `str`. | L140: Docstring: Decode a JSON string body safely; fall back to unescaping quotes only. | L141: Blok `try` — chroniony kod, potem except/finally. | L142: Zwraca: `json.loads(f'"{val}"')`. | L143: Przechwytuje wyjątek `Exception`. | L144: Zwraca: `val.replace(r"\"", '"')`. | L145:  | L146:  | L147: Definicja funkcji/metody `parse_model_json`, zwraca `dict[str, Any]`. | L148: Blok `try` — chroniony kod, potem except/finally. | L149: Przypisanie `data` ← `json.loads(raw_content.strip())`. | L150: Warunek `if` — gdy `isinstance(data, dict)`. | L151: Zwraca: `data`. | L152: Przechwytuje wyjątek `(json.JSONDecodeError, ValueError)`. | L153: Puste ciało (`pass`) — znacznik pakietu lub placeholder. | L154:  | L155: Komentarz: Non-recursive brace match (Python re has no (?R)) | L156: Przypisanie `json_match` ← `re.search(r"\{.*?\}", raw_content, re.DOTALL)`. | L157: Warunek `if` — gdy `json_match`. | L158: Blok `try` — chroniony kod, potem except/finally. | L159: Przypisanie `data` ← `json.loads(json_match.group(0).strip())`. | L160: Warunek `if` — gdy `isinstance(data, dict)`. | L161: Zwraca: `data`. | L162: Przechwytuje wyjątek `(json.JSONDecodeError, ValueError)`. | L163: Puste ciało (`pass`) — znacznik pakietu lub placeholder. | L164:  | L165: Przypisanie `ans_match` ← `re.search(r'"answer"\s*:\s*"((?:\\.|[^"\\])*)"', raw_content)`. | L166: Przypisanie `score_match` ← `re.search(r'"prompt_score"\s*:\s*(\d+)', raw_content)`. | L167: Przypisanie `feedback_match` ← `re.search(`. | L168: Wykonuje: `r'"prompt_feedback"\s*:\s*"((?:\\.|[^"\\])*)"', raw_content`. | L169: Zamknięcie wyrażenia (`)`). | L170: Przypisanie `penalty_match` ← `re.search(`. | L171: Wykonuje: `r'"penalty_applied"\s*:\s*(true|false)', raw_content, re.IGNORECASE`. | L172: Zamknięcie wyrażenia (`)`). | L173:  | L174: Warunek `if` — gdy `ans_match`. | L175: Zwraca: `{`. | L176: Element listy/argumentów: `"answer": _safe_decode_json_string(ans_match.group(1)),`. | L177: Element listy/argumentów: `"prompt_score": int(score_match.group(1)) if score_match else 5,`. | L178: Wykonuje: `"prompt_feedback": (`. | L179: Wykonuje: `_safe_decode_json_string(feedback_match.group(1))`. | L180: Warunek `if` — gdy `feedback_match`. | L181: Wykonuje: `else ""`. | L182: Element listy/argumentów: `),`. | L183: Wykonuje: `"penalty_applied": (`. | L184: Przypisanie `penalty_match.group(1).lower()` ← `= "true" if penalty_match else False`. | L185: Element listy/argumentów: `),`. | L186: Zamknięcie wyrażenia (`}`). | L187:  | L188: Zwraca: `{`. | L189: Element listy/argumentów: `"answer": raw_content,`. | L190: Element listy/argumentów: `"prompt_score": 3,`. | L191: Wykonuje: `"prompt_feedback": (`. | L192: Wykonuje: `"Zadawaj pytania precyzyjniej, załączając fragmenty kodu."`. | L193: Warunek `if` — gdy `language == "pl"`. | L194: Wykonuje: `else "Please ask more specific questions."`. | L195: Element listy/argumentów: `),`. | L196: Element listy/argumentów: `"penalty_applied": False,`. | L197: Zamknięcie wyrażenia (`}`). | L198:  | L199:  | L200: Definicja funkcji/metody `?`. | L201: Element listy/argumentów: `answer_text: str,`. | L202: Element listy/argumentów: `score: int,`. | L203: Element listy/argumentów: `penalty_applied: bool,`. | L204: Element listy/argumentów: `conversation: Conversation,`. | L205: Wykonuje: `) -> tuple[str, int, bool]:`. | L206: Warunek `if` — gdy `contains_revealed_code(answer_text)`. | L207: Zwraca: `code_reveal_fallback(conversation), 1, True`. | L208: Zwraca: `answer_text, score, penalty_applied`. | L209:  | L210:  | L211: Definicja funkcji/metody `?`. | L212: Element listy/argumentów: `raw_content: str,`. | L213: Element listy/argumentów: `conversation: Conversation,`. | L214: Element listy/argumentów: `*,`. | L215: Element listy/argumentów: `message_id: str,`. | L216: Element listy/argumentów: `tokens_used: int,`. | L217: Element listy/argumentów: `code_changed: bool,`. | L218: Element listy/argumentów: `was_frustrated: bool,`. | L219: Przypisanie `sources: list[dict] | None` ← `None,`. | L220: Wykonuje: `) -> dict[str, Any]:`. | L221: Przypisanie `lang` ← `conversation.config.language`. | L222: Przypisanie `result_data` ← `parse_model_json(raw_content, lang)`. | L223:  | L224: Przypisanie `answer_text` ← `str(result_data.get("answer", raw_content)).strip()`. | L225: Przypisanie `score` ← `int(result_data.get("prompt_score", 3))`. | L226: Przypisanie `feedback_text` ← `str(result_data.get("prompt_feedback", "")).strip()`. | L227: Przypisanie `penalty_applied` ← `bool(result_data.get("penalty_applied", False))`. | L228: Przypisanie `suggested_next_step` ← `str(result_data.get("suggested_next_step") or "").strip() or None`. | L229:  | L230: Przypisanie `goals` ← `conversation.config.learningContext.goals or []`. | L231: Przypisanie `raw_progress` ← `result_data.get("goal_progress") or []`. | L232: Przypisanie `goal_progress: list[dict[str, str]]` ← `[]`. | L233: Warunek `if` — gdy `isinstance(raw_progress, list)`. | L234: Pętla `for` po `item in raw_progress`. | L235: Warunek `if` — gdy `not isinstance(item, dict)`. | L236: Przechodzi do kolejnej iteracji pętli (`continue`). | L237: Przypisanie `goal` ← `str(item.get("goal", "")).strip()`. | L238: Przypisanie `status` ← `str(item.get("status", "not_started")).strip()`. | L239: Warunek `if` — gdy `status not in ("not_started", "in_progress", "done")`. | L240: Przypisanie `status` ← `"not_started"`. | L241: Warunek `if` — gdy `goal`. | L242: Wykonuje: `goal_progress.append({"goal": goal, "status": status})`. | L243: Warunek `if` — gdy `not goal_progress and goals`. | L244: Przypisanie `goal_progress` ← `[{"goal": g, "status": "in_progress"} for g in goals[:3]]`. | L245:  | L246: Przypisanie `answer_text, score, penalty_applied` ← `apply_code_penalty(`. | L247: Wykonuje: `answer_text, score, penalty_applied, conversation`. | L248: Zamknięcie wyrażenia (`)`). | L249:  | L250: Wykonuje: `conversation.messages.append(`. | L251: Wykonuje: `{`. | L252: Element listy/argumentów: `"role": "assistant",`. | L253: Element listy/argumentów: `"content": answer_text,`. | L254: Element listy/argumentów: `"message_id": message_id,`. | L255: Element listy/argumentów: `"penalty_applied": penalty_applied,`. | L256: Element listy/argumentów: `"prompt_score": score,`. | L257: Element listy/argumentów: `"sources": sources or [],`. | L258: Element listy/argumentów: `"suggested_next_step": suggested_next_step,`. | L259: Element listy/argumentów: `"goal_progress": goal_progress,`. | L260: Zamknięcie wyrażenia (`}`). | L261: Zamknięcie wyrażenia (`)`). | L262: Wykonuje: `conversation.prompt_scores.append(score)`. | L263: Przypisanie `conversation.tokens_used_total +` ← `int(tokens_used or 0)`. | L264: Wykonuje: `conversation.touch()`. | L265:  | L266: Zwraca: `{`. | L267: Element listy/argumentów: `"message_id": message_id,`. | L268: Element listy/argumentów: `"answer": answer_text,`. | L269: Element listy/argumentów: `"prompt_score": score,`. | L270: Element listy/argumentów: `"prompt_feedback": feedback_text,`. | L271: Element listy/argumentów: `"penalty_applied": penalty_applied,`. | L272: Element listy/argumentów: `"tokens_used": tokens_used,`. | L273: Element listy/argumentów: `"is_cached": False,`. | L274: Element listy/argumentów: `"sources": sources or [],`. | L275: Element listy/argumentów: `"suggested_next_step": suggested_next_step,`. | L276: Element listy/argumentów: `"goal_progress": goal_progress,`. | L277: Wykonuje: `"debug_info": {`. | L278: Komentarz: Current streak after this score (was_frustrated is pre-turn pedagogy only). | L279: Element listy/argumentów: `"is_frustrated": conversation.is_frustrated,`. | L280: Element listy/argumentów: `"avg_score": round(recent_avg_score(conversation.prompt_scores), 2),`. | L281: Element listy/argumentów: `"code_changed": code_changed,`. | L282: Element listy/argumentów: `},`. | L283: Zamknięcie wyrażenia (`}`). | L284:  | L285:  | L286: Definicja funkcji/metody `llm_error_fallback`, zwraca `dict[str, Any]`. | L287: Przypisanie `is_en` ← `language == "en"`. | L288: Zwraca: `{`. | L289: Element listy/argumentów: `"message_id": message_id,`. | L290: Wykonuje: `"answer": (`. | L291: Wykonuje: `"Sorry, the model server hit a temporary technical issue. Please try asking again."`. | L292: Warunek `if` — gdy `is_en`. | L293: Wykonuje: `else "Przepraszam, serwer modelu napotkał chwilowy problem techniczny. Spróbuj powtórzyć pytanie."`. | L294: Element listy/argumentów: `),`. | L295: Element listy/argumentów: `"prompt_score": 5,`. | L296: Element listy/argumentów: `"prompt_feedback": "External LLM API error." if is_en else "Błąd zewnętrznego API LLM.",`. | L297: Element listy/argumentów: `"penalty_applied": False,`. | L298: Element listy/argumentów: `"tokens_used": 0,`. | L299: Element listy/argumentów: `"is_cached": False,`. | L300: Element listy/argumentów: `"sources": [],`. | L301: Element listy/argumentów: `"suggested_next_step": None,`. | L302: Element listy/argumentów: `"goal_progress": [],`. | L303: Zamknięcie wyrażenia (`}`). | L304:  | L305:  | L306: Przypisanie `_IDENTIFIER_RE` ← `re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]{3,}\b")`. | L307:  | L308: Przypisanie `_IDENTIFIER_STOP` ← `{`. | L309: Element listy/argumentów: `"File",`. | L310: Element listy/argumentów: `"Code",`. | L311: Element listy/argumentów: `"Plik",`. | L312: Element listy/argumentów: `"Kod",`. | L313: Element listy/argumentów: `"None",`. | L314: Element listy/argumentów: `"Brak",`. | L315: Element listy/argumentów: `"Student",`. | L316: Element listy/argumentów: `"question",`. | L317: Element listy/argumentów: `"Pytanie",`. | L318: Element listy/argumentów: `"studenta",`. | L319: Element listy/argumentów: `"Error",`. | L320: Element listy/argumentów: `"logs",`. | L321: Element listy/argumentów: `"Logi",`. | L322: Element listy/argumentów: `"class",`. | L323: Element listy/argumentów: `"Test",`. | L324: Element listy/argumentów: `"java",`. | L325: Element listy/argumentów: `"Java",`. | L326: Zamknięcie wyrażenia (`}`). | L327:  | L328:  | L329: Definicja funkcji/metody `collect_identifier_tokens`, zwraca `list[str]`. | L330: Docstring: Prefer snake_case / camelCase tokens that look like student-named identifiers. | L331: Przypisanie `found: list[str]` ← `[]`. | L332: Przypisanie `seen: set[str]` ← `set()`. | L333: Pętla `for` po `tok in _IDENTIFIER_RE.findall(text or "")`. | L334: Warunek `if` — gdy `tok in _IDENTIFIER_STOP or tok.lower() in seen`. | L335: Przechodzi do kolejnej iteracji pętli (`continue`). | L336: Warunek `if` — gdy `"_" in tok or (any(c.isupper() for c in tok[1:]) and tok[0].islower())`. | L337: Wykonuje: `seen.add(tok.lower())`. | L338: Wykonuje: `found.append(tok)`. | L339: Warunek `if` — gdy `len(found) >= limit`. | L340: Przerywa pętlę (`break`). | L341: Zwraca: `found`. | L342:  | L343:  | L344: Definicja funkcji/metody `_extract_pinned_facts`, zwraca `str`. | L345: Docstring: Pull student-stated identifiers from early turns so compression does not erase them. | L346: Przypisanie `blob` ← `"\n".join(`. | L347: Wykonuje: `str(m.get("content") or "")`. | L348: Pętla `for` po `m in early_messages`. | L349: Warunek `if` — gdy `m.get("role") == "user"`. | L350: Zamknięcie wyrażenia (`)`). | L351: Przypisanie `found` ← `collect_identifier_tokens(blob, limit=limit)`. | L352: Warunek `if` — gdy `not found`. | L353: Zwraca: `""`. | L354: Przypisanie `label` ← `"Pinned student identifiers:" if language == "en" else "Zachowane ide…`. | L355: Zwraca: `f"{label} {', '.join(found)}"`. | L356:  | L357:  | L358: Definicja funkcji/metody `format_pinned_identifiers_note`, zwraca `str`. | L359: Warunek `if` — gdy `not identifiers`. | L360: Zwraca: `""`. | L361: Przypisanie `joined` ← `", ".join(identifiers)`. | L362: Warunek `if` — gdy `language == "en"`. | L363: Zwraca: `(`. | L364: Wykonuje: `"Pinned student identifiers (repeat exactly if asked): "`. | L365: Wykonuje: `f"{joined}"`. | L366: Zamknięcie wyrażenia (`)`). | L367: Zwraca: `(`. | L368: Wykonuje: `"Zachowane identyfikatory studenta (powtórz dokładnie, gdy pyta): "`. | L369: Wykonuje: `f"{joined}"`. | L370: Zamknięcie wyrażenia (`)`). | L371:  | L372: Definicja funkcji/metody `?`. | L373: Przypisanie `messages: list[dict], language: str, max_length: int` ← `16`. | L374: Wykonuje: `) -> list[dict]:`. | L375: Warunek `if` — gdy `len(messages) <= max_length`. | L376: Zwraca: `messages`. | L377:  | L378: Przypisanie `head: list[dict]` ← `[messages[0]]`. | L379: Warunek `if` — gdy `len(messages) > 1 and messages[1].get("role") == "assistant"`. | L380: Wykonuje: `head.append(messages[1])`. | L381:  | L382: Przypisanie `recent_count` ← `8`. | L383: Przypisanie `recent_slice` ← `messages[-recent_count:]`. | L384: Warunek `if` — gdy `recent_slice and recent_slice[0].get("role") == "assistant" and len(messages) > recent_count`. | L385: Przypisanie `recent_slice` ← `messages[-(recent_count + 1) :]`. | L386:  | L387: Komentarz: Avoid duplicating messages already kept in the head | L388: Przypisanie `head_ids` ← `{id(m) for m in head}`. | L389: Przypisanie `recent_slice` ← `[m for m in recent_slice if id(m) not in head_ids]`. | L390:  | L391: Przypisanie `pinned` ← `_extract_pinned_facts(messages[:6], language)`. | L392: Warunek `if` — gdy `language == "en"`. | L393: Przypisanie `note_body` ← `(`. | L394: Wykonuje: `"[System note: Middle conversation turns trimmed for performance. "`. | L395: Wykonuje: `"Initial context preserved.]"`. | L396: Zamknięcie wyrażenia (`)`). | L397: Gałąź `else` (pozostałe przypadki). | L398: Przypisanie `note_body` ← `(`. | L399: Wykonuje: `"[Notatka systemu: Środkowa część rozmowy została skrócona. "`. | L400: Wykonuje: `"Początkowe ustalenia zostały zachowane.]"`. | L401: Zamknięcie wyrażenia (`)`). | L402: Warunek `if` — gdy `pinned`. | L403: Warunek `if` — gdy `language == "en"`. | L404: Przypisanie `recall` ← `(`. | L405: Wykonuje: `"When the student asks for a name they gave earlier, "`. | L406: Wykonuje: `"repeat it EXACTLY from the list below — do not invent a substitute."`. | L407: Zamknięcie wyrażenia (`)`). | L408: Gałąź `else` (pozostałe przypadki). | L409: Przypisanie `recall` ← `(`. | L410: Wykonuje: `"Gdy student pyta o nazwę podaną wcześniej, "`. | L411: Wykonuje: `"powtórz ją DOKŁADNIE z listy poniżej — nie wymyślaj zamiennika."`. | L412: Zamknięcie wyrażenia (`)`). | L413: Przypisanie `note_body` ← `f"{note_body}\n{recall}\n{pinned}"`. | L414:  | L415: Przypisanie `info_note` ← `{"role": "system", "content": note_body}`. | L416: Zwraca: `head + [info_note] + recent_slice`.

<a id="app-application-sessions-py"></a>
## `app/application/sessions.py`
Zarządzanie sesjami konwersacji (TTL, cap, state, export, idempotency, delete).

Liczba linii: **262**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L7:** Importy — L3: `import logging`; L4: `import re`; L5: `import uuid`; L6: `from datetime import datetime, timezone`; L7: `from typing import TYPE_CHECKING`.
- **L9–L17:** Importy — L9: `from app.api.schemas.requests import IdeEventRequest`; L10: `from app.core.config import CONVERSATION_TTL, MAX_CONVERSATIONS`; L11: `from app.domain.conversation import Conversation, recent_avg_score`; L12: `from app.domain.exceptions import (`; L13: `PrelabRequired,`; L14: `TokenBudgetExceeded,`; L15: `UnknownConversation,`; L16: `)`; L17: `from app.domain.sensei import SenseiConfig`.
- **L19:** Warunek `if` — gdy `TYPE_CHECKING`.
- **L20–L20:** Importy — L20: `from app.application.container import AppContainer`.
- **L22:** Przypisanie `logger` ← `logging.getLogger(__name__)`.
- **L25:** Definicja klasy `SessionService`.
- **L26:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L27:** (w `SessionService`) Przypisanie `self._app` ← `app`.
- **L29:** Definicja funkcji/metody `purge_stale_conversations`, zwraca `int`.
- **L30:** (w `SessionService`) Przypisanie `now` ← `datetime.now(timezone.utc)`.
- **L31–L35:** (w `SessionService`) Wyrażenie wieloliniowe — L31: Przypisanie `stale` ← `[`. | L32: Wykonuje: `cid`. | L33: Pętla `for` po `cid, conv in self._app.conversations.items()`. | L34: Warunek `if` — gdy `now - conv.last_active_at > CONVERSATION_TTL`. | L35: Zamknięcie wyrażenia (`]`).
- **L36:** (w `SessionService`) Pętla `for` po `cid in stale`.
- **L37:** (w `SessionService`) Wykonuje: `self._app.rag.delete_conversation_data(cid)`.
- **L38:** (w `SessionService`) Wykonuje: `del self._app.conversations[cid]`.
- **L39:** (w `SessionService`) Zwraca: `len(stale)`.
- **L41:** Definicja funkcji/metody `_enforce_conversation_cap`, zwraca `None`.
- **L42:** (w `SessionService`) Warunek `if` — gdy `len(self._app.conversations) < MAX_CONVERSATIONS`.
- **L43:** (w `SessionService`) Zwraca `None`.
- **L44–L46:** (w `SessionService`) Wyrażenie wieloliniowe — L44: Przypisanie `ordered` ← `sorted(`. | L45: Przypisanie `self._app.conversations.items(), key` ← `lambda item: item[1].last_active_at`. | L46: Zamknięcie wyrażenia (`)`).
- **L47:** (w `SessionService`) Przypisanie `overflow` ← `len(self._app.conversations) - MAX_CONVERSATIONS + 1`.
- **L48:** (w `SessionService`) Pętla `for` po `cid, _ in ordered[:overflow]`.
- **L49:** (w `SessionService`) Wykonuje: `self._app.rag.delete_conversation_data(cid)`.
- **L50:** (w `SessionService`) Wykonuje: `del self._app.conversations[cid]`.
- **L52:** Definicja funkcji/metody `start_conversation`, zwraca `str`.
- **L53:** (w `SessionService`) Wykonuje: `self.purge_stale_conversations()`.
- **L54:** (w `SessionService`) Wykonuje: `self._enforce_conversation_cap()`.
- **L55:** (w `SessionService`) Przypisanie `conversation_id` ← `str(uuid.uuid4())`.
- **L56:** (w `SessionService`) Przypisanie `prelab_needed` ← `bool(config.preLab and config.preLab.enabled)`.
- **L57–L64:** (w `SessionService`) Wyrażenie wieloliniowe — L57: Przypisanie `self._app.conversations[conversation_id]` ← `Conversation(`. | L58: Przypisanie `problem` ← `problem,`. | L59: Przypisanie `config` ← `config,`. | L60: Przypisanie `messages` ← `[],`. | L61: Przypisanie `prompt_scores` ← `[],`. | L62: Przypisanie `last_code` ← `"",`. | L63: Przypisanie `prelab_passed` ← `not prelab_needed,`. | L64: Zamknięcie wyrażenia (`)`).
- **L65:** (w `SessionService`) Wykonuje: `self._app.conversations[conversation_id].ensure_goal_progress_defaults()`.
- **L66:** (w `SessionService`) Zwraca: `conversation_id`.
- **L68:** Definicja funkcji/metody `get_conversation_or_404`, zwraca `Conversation`.
- **L69:** (w `SessionService`) Przypisanie `conversation` ← `self._app.conversations.get(conversation_id)`.
- **L70:** (w `SessionService`) Warunek `if` — gdy `not conversation`.
- **L71:** (w `SessionService`) Rzuca wyjątek: `UnknownConversation(conversation_id)`.
- **L72:** (w `SessionService`) Zwraca: `conversation`.
- **L74:** Definicja funkcji/metody `ensure_prelab_passed`, zwraca `None`.
- **L75:** (w `SessionService`) Przypisanie `prelab` ← `conversation.config.preLab`.
- **L76:** (w `SessionService`) Warunek `if` — gdy `prelab and prelab.enabled and not conversation.prelab_passed`.
- **L77:** (w `SessionService`) Rzuca wyjątek: `PrelabRequired()`.
- **L79:** Definicja funkcji/metody `ensure_token_budget`, zwraca `None`.
- **L80:** (w `SessionService`) Przypisanie `limit` ← `conversation.config.maxTokensPerSession`.
- **L81:** (w `SessionService`) Warunek `if` — gdy `limit is not None and conversation.tokens_used_total >= limit`.
- **L82:** (w `SessionService`) Rzuca wyjątek: `TokenBudgetExceeded()`.
- **L84:** Definicja funkcji/metody `get_session_state`, zwraca `dict`.
- **L85:** (w `SessionService`) Przypisanie `conv` ← `self.get_conversation_or_404(conversation_id)`.
- **L86:** (w `SessionService`) Wykonuje: `conv.touch()`.
- **L87:** (w `SessionService`) Przypisanie `avg` ← `recent_avg_score(conv.prompt_scores)`.
- **L88–L111:** (w `SessionService`) Wyrażenie wieloliniowe — L88: Zwraca: `{`. | L89: Element listy/argumentów: `"conversation_id": conversation_id,`. | L90: Element listy/argumentów: `"problem": conv.problem,`. | L91: Element listy/argumentów: `"language": conv.config.language,`. | L92: Element listy/argumentów: `"goals": conv.config.learningContext.goals,`. | L93: Wykonuje: `"ideRestrictions": (`. | L94: Wykonuje: `conv.config.ideRestrictions.model_dump()`. | L95: Warunek `if` — gdy `conv.config.ideRestrictions`. | L96: Wykonuje: `else None`. | L97: Element listy/argumentów: `),`. | L98: Element listy/argumentów: `"prelab_passed": conv.prelab_passed,`. | L99: Element listy/argumentów: `"prelab_required": bool(conv.config.preLab and conv.config.preLab.enabled),`. | L100: Element listy/argumentów: `"message_count": len(conv.messages),`. | L101: Element listy/argumentów: `"avg_score": round(avg, 2),`. | L102: Element listy/argumentów: `"tokens_used_total": conv.tokens_used_total,`. | L103: Element listy/argumentów: `"max_tokens_per_session": conv.config.maxTokensPerSession,`. | L104: Element listy/argumentów: `"is_frustrated": conv.is_frustrated,`. | L105: Element listy/argumentów: `"reveal_count": conv.reveal_count,`. | L106: Element listy/argumentów: `"ide_event_count": len(conv.ide_events),`. | L107: Element listy/argumentów: `"mode": conv.config.agentBehavior.mode,`. | L108: Element listy/argumentów: `"unlocked_checkpoints": list(conv.unlocked_checkpoints),`. | L109: Element listy/argumentów: `"prelab_attempts": conv.prelab_attempts,`. | L110: Element listy/argumentów: `"last_prelab_score": conv.last_prelab_score,`. | L111: Zamknięcie wyrażenia (`}`).
- **L113:** Definicja funkcji/metody `get_message_history`, zwraca `dict`.
- **L114:** (w `SessionService`) Przypisanie `conv` ← `self.get_conversation_or_404(conversation_id)`.
- **L115:** (w `SessionService`) Wykonuje: `conv.touch()`.
- **L116:** (w `SessionService`) Przypisanie `items` ← `[]`.
- **L117:** (w `SessionService`) Pętla `for` po `m in conv.messages`.
- **L118:** (w `SessionService`) Przypisanie `role` ← `m.get("role")`.
- **L119:** (w `SessionService`) Warunek `if` — gdy `role not in ("user", "assistant")`.
- **L120:** (w `SessionService`) Przechodzi do kolejnej iteracji pętli (`continue`).
- **L121:** (w `SessionService`) Przypisanie `content` ← `m.get("content", "")`.
- **L122:** (w `SessionService`) Warunek `if` — gdy `role == "user"`.
- **L123:** (w `SessionService`) Komentarz: Prefer the student question line if present
- **L124–L128:** (w `SessionService`) Wyrażenie wieloliniowe — L124: Przypisanie `match` ← `re.search(`. | L125: Element listy/argumentów: `r"(?:Student question|Pytanie studenta):\s*(.*)$",`. | L126: Element listy/argumentów: `content,`. | L127: Element listy/argumentów: `re.MULTILINE,`. | L128: Zamknięcie wyrażenia (`)`).
- **L129:** (w `SessionService`) Przypisanie `content` ← `match.group(1).strip() if match else content[:500]`.
- **L130–L141:** (w `SessionService`) Wyrażenie wieloliniowe — L130: Wykonuje: `items.append(`. | L131: Wykonuje: `{`. | L132: Element listy/argumentów: `"role": role,`. | L133: Element listy/argumentów: `"content": content,`. | L134: Element listy/argumentów: `"message_id": m.get("message_id"),`. | L135: Element listy/argumentów: `"prompt_score": m.get("prompt_score"),`. | L136: Element listy/argumentów: `"penalty_applied": m.get("penalty_applied", False),`. | L137: Element listy/argumentów: `"sources": m.get("sources") or [],`. | L138: Element listy/argumentów: `"suggested_next_step": m.get("suggested_next_step"),`. | L139: Element listy/argumentów: `"goal_progress": m.get("goal_progress") or [],`. | L140: Zamknięcie wyrażenia (`}`). | L141: Zamknięcie wyrażenia (`)`).
- **L142:** (w `SessionService`) Zwraca: `{"conversation_id": conversation_id, "messages": items}`.
- **L144:** Definicja funkcji/metody `get_restrictions`, zwraca `dict`.
- **L145:** (w `SessionService`) Przypisanie `conv` ← `self.get_conversation_or_404(conversation_id)`.
- **L146:** (w `SessionService`) Przypisanie `restrictions` ← `conv.config.ideRestrictions`.
- **L147–L158:** (w `SessionService`) Wyrażenie wieloliniowe — L147: Zwraca: `{`. | L148: Element listy/argumentów: `"conversation_id": conversation_id,`. | L149: Wykonuje: `"requireFileContextForChat": bool(`. | L150: Wykonuje: `restrictions and restrictions.requireFileContextForChat`. | L151: Element listy/argumentów: `),`. | L152: Wykonuje: `"disableCopyFromChat": bool(`. | L153: Wykonuje: `restrictions and restrictions.disableCopyFromChat`. | L154: Element listy/argumentów: `),`. | L155: Element listy/argumentów: `"maxTokensPerSession": conv.config.maxTokensPerSession,`. | L156: Element listy/argumentów: `"prelab_required": bool(conv.config.preLab and conv.config.preLab.enabled),`. | L157: Element listy/argumentów: `"prelab_passed": conv.prelab_passed,`. | L158: Zamknięcie wyrażenia (`}`).
- **L160:** Definicja funkcji/metody `record_ide_event`, zwraca `dict`.
- **L161:** (w `SessionService`) Przypisanie `conv` ← `self.get_conversation_or_404(conversation_id)`.
- **L162–L166:** (w `SessionService`) Wyrażenie wieloliniowe — L162: Przypisanie `event` ← `{`. | L163: Element listy/argumentów: `"type": payload.type,`. | L164: Element listy/argumentów: `"meta": payload.meta,`. | L165: Element listy/argumentów: `"at": datetime.now(timezone.utc).isoformat(),`. | L166: Zamknięcie wyrażenia (`}`).
- **L167:** (w `SessionService`) Wykonuje: `conv.ide_events.append(event)`.
- **L168:** (w `SessionService`) Wykonuje: `conv.touch()`.
- **L169:** (w `SessionService`) Zwraca: `{"status": "ok", "event": event, "total_events": len(conv.ide_events)}`.
- **L171:** Definicja funkcji/metody `export_conversation`, zwraca `dict`.
- **L172:** (w `SessionService`) Przypisanie `conv` ← `self.get_conversation_or_404(conversation_id)`.
- **L173:** (w `SessionService`) Wykonuje: `conv.touch()`.
- **L174:** (w `SessionService`) Przypisanie `history` ← `self.get_message_history(conversation_id)`.
- **L175–L192:** (w `SessionService`) Wyrażenie wieloliniowe — L175: Zwraca: `{`. | L176: Element listy/argumentów: `"conversation_id": conversation_id,`. | L177: Element listy/argumentów: `"problem": conv.problem,`. | L178: Element listy/argumentów: `"config": conv.config.model_dump(),`. | L179: Element listy/argumentów: `"messages": history["messages"],`. | L180: Element listy/argumentów: `"prompt_scores": list(conv.prompt_scores),`. | L181: Element listy/argumentów: `"ide_events": list(conv.ide_events),`. | L182: Element listy/argumentów: `"goal_progress": list(conv.goal_progress),`. | L183: Element listy/argumentów: `"unlocked_checkpoints": list(conv.unlocked_checkpoints),`. | L184: Element listy/argumentów: `"tokens_used_total": conv.tokens_used_total,`. | L185: Element listy/argumentów: `"prelab_passed": conv.prelab_passed,`. | L186: Element listy/argumentów: `"prelab_attempts": conv.prelab_attempts,`. | L187: Element listy/argumentów: `"last_prelab_score": conv.last_prelab_score,`. | L188: Element listy/argumentów: `"summary": conv.last_summary,`. | L189: Element listy/argumentów: `"summary_generated": conv.summary_generated,`. | L190: Element listy/argumentów: `"created_at": conv.created_at.isoformat(),`. | L191: Element listy/argumentów: `"last_active_at": conv.last_active_at.isoformat(),`. | L192: Zamknięcie wyrażenia (`}`).
- **L194:** Definicja funkcji/metody `get_checkpoints`, zwraca `dict`.
- **L195:** (w `SessionService`) Przypisanie `conv` ← `self.get_conversation_or_404(conversation_id)`.
- **L196:** (w `SessionService`) Wykonuje: `conv.ensure_goal_progress_defaults()`.
- **L197–L199:** (w `SessionService`) Wyrażenie wieloliniowe — L197: Przypisanie `done_goals` ← `{`. | L198: Przypisanie `g["goal"] for g in conv.goal_progress if g.get("status")` ← `= "done"`. | L199: Zamknięcie wyrażenia (`}`).
- **L200:** (w `SessionService`) Przypisanie `items` ← `[]`.
- **L201:** (w `SessionService`) Pętla `for` po `cp in conv.config.checkpoints`.
- **L202–L204:** (w `SessionService`) Wyrażenie wieloliniowe — L202: Przypisanie `unlocked` ← `cp.id in conv.unlocked_checkpoints or (`. | L203: Wykonuje: `cp.after_goal is None or cp.after_goal in done_goals`. | L204: Zamknięcie wyrażenia (`)`).
- **L205:** (w `SessionService`) Warunek `if` — gdy `unlocked and cp.id not in conv.unlocked_checkpoints`.
- **L206:** (w `SessionService`) Wykonuje: `conv.unlocked_checkpoints.append(cp.id)`.
- **L207–L215:** (w `SessionService`) Wyrażenie wieloliniowe — L207: Wykonuje: `items.append(`. | L208: Wykonuje: `{`. | L209: Element listy/argumentów: `"id": cp.id,`. | L210: Element listy/argumentów: `"after_goal": cp.after_goal,`. | L211: Element listy/argumentów: `"hint": cp.hint,`. | L212: Wykonuje: `"unlocked": cp.id in conv.unlocked_checkpoints`. | L213: Element listy/argumentów: `or (cp.after_goal is None or cp.after_goal in done_goals),`. | L214: Zamknięcie wyrażenia (`}`). | L215: Zamknięcie wyrażenia (`)`).
- **L216:** (w `SessionService`) Wykonuje: `conv.touch()`.
- **L217:** (w `SessionService`) Zwraca: `{"conversation_id": conversation_id, "checkpoints": items}`.
- **L219–L221:** (w `SessionService`) Wyrażenie wieloliniowe — L219: Definicja funkcji/metody `?`. | L220: Wykonuje: `self, conversation_id: str, client_message_id: str | None`. | L221: Wykonuje: `) -> dict | None:`.
- **L222:** (w `SessionService`) Warunek `if` — gdy `not client_message_id`.
- **L223:** (w `SessionService`) Zwraca: `None`.
- **L224:** (w `SessionService`) Przypisanie `conv` ← `self.get_conversation_or_404(conversation_id)`.
- **L225:** (w `SessionService`) Przypisanie `cached` ← `conv.idempotency.get(client_message_id)`.
- **L226:** (w `SessionService`) Warunek `if` — gdy `cached`.
- **L227:** (w `SessionService`) Przypisanie `result` ← `dict(cached)`.
- **L228:** (w `SessionService`) Przypisanie `result["is_cached"]` ← `True`.
- **L229:** (w `SessionService`) Przypisanie `result["client_message_id"]` ← `client_message_id`.
- **L230:** (w `SessionService`) Zwraca: `result`.
- **L231:** (w `SessionService`) Zwraca: `None`.
- **L233–L235:** (w `SessionService`) Wyrażenie wieloliniowe — L233: Definicja funkcji/metody `?`. | L234: Wykonuje: `self, conversation_id: str, client_message_id: str | None, result: dict`. | L235: Wykonuje: `) -> dict:`.
- **L236:** (w `SessionService`) Warunek `if` — gdy `client_message_id`.
- **L237:** (w `SessionService`) Przypisanie `conv` ← `self.get_conversation_or_404(conversation_id)`.
- **L238:** (w `SessionService`) Przypisanie `payload` ← `dict(result)`.
- **L239:** (w `SessionService`) Przypisanie `payload["client_message_id"]` ← `client_message_id`.
- **L240:** (w `SessionService`) Przypisanie `conv.idempotency[client_message_id]` ← `payload`.
- **L241:** (w `SessionService`) Przypisanie `result` ← `payload`.
- **L242:** (w `SessionService`) Zwraca: `result`.
- **L244–L246:** (w `SessionService`) Wyrażenie wieloliniowe — L244: Definicja funkcji/metody `?`. | L245: Przypisanie `self, conversation_id: str, *, soft_summary: bool` ← `True`. | L246: Wykonuje: `) -> dict:`.
- **L247:** (w `SessionService`) Przypisanie `conv` ← `self._app.conversations.get(conversation_id)`.
- **L248:** (w `SessionService`) Warunek `if` — gdy `conv is None`.
- **L249:** (w `SessionService`) Rzuca wyjątek: `UnknownConversation(conversation_id)`.
- **L250:** (w `SessionService`) Przypisanie `summary` ← `None`.
- **L251:** (w `SessionService`) Warunek `if` — gdy `soft_summary and not conv.summary_generated and conv.messages`.
- **L252:** (w `SessionService`) Blok `try` — chroniony kod, potem except/finally.
- **L253:** (w `SessionService`) Przypisanie `summary` ← `await self._app.summary.generate_summary(conversation_id)`.
- **L254:** (w `SessionService`) Przechwytuje wyjątek `Exception as exc`.
- **L255:** (w `SessionService`) Log: `logger.warning("Soft summary on delete failed: %s", exc)`.
- **L256:** (w `SessionService`) Wykonuje: `self._app.conversations.pop(conversation_id, None)`.
- **L257:** (w `SessionService`) Wykonuje: `self._app.rag.delete_conversation_data(conversation_id)`.
- **L258–L262:** (w `SessionService`) Wyrażenie wieloliniowe — L258: Zwraca: `{`. | L259: Element listy/argumentów: `"status": "deleted",`. | L260: Element listy/argumentów: `"conversation_id": conversation_id,`. | L261: Element listy/argumentów: `"summary": summary,`. | L262: Zamknięcie wyrażenia (`}`).

<a id="app-application-prompts-py"></a>
## `app/application/prompts.py`
Budowa system promptu i formatowanie bloku kontekstu kodu.

Liczba linii: **188**.

### Opis linia-po-linii

- **L1:** Docstring: System prompts and code-context formatting.
- **L3–L3:** Importy — L3: `from __future__ import annotations`.
- **L5–L5:** Importy — L5: `import re`.
- **L7–L12:** Importy — L7: `from app.domain.conversation import (`; L8: `FRUSTRATION_STREAK,`; L9: `Conversation,`; L10: `consecutive_low_scores,`; L11: `)`; L12: `from app.domain.sensei import CodeContext`.
- **L14–L25:** Wyrażenie wieloliniowe — L14: Przypisanie `_MODE_DELTA` ← `{`. | L15: Wykonuje: `"en": {`. | L16: Element listy/argumentów: `"theory": "Mode theory: explain clearly, low Socratic pressure, skip IDE noise unless asked.",`. | L17: Element listy/argumentów: `"debug": "Mode debug: focus on code, selection, diagnostics; guide with questions when stuck.",`. | L18: Element listy/argumentów: `"review": "Mode review: conceptual findings and guiding questions only — no full patches.",`. | L19: Element listy/argumentów: `},`. | L20: Wykonuje: `"pl": {`. | L21: Element listy/argumentów: `"theory": "Tryb theory: jasne wyjaśnienia, mniejszy rygor sokratyczny, bez zbędnej diagnostyki IDE.",`. | L22: Element listy/argumentów: `"debug": "Tryb debug: kod, zaznaczenie, diagnostyki; pytania naprowadzające przy problemach.",`. | L23: Element listy/argumentów: `"review": "Tryb review: uwagi koncepcyjne i pytania — bez pełnego patcha ani gotowego rozwiązania.",`. | L24: Element listy/argumentów: `},`. | L25: Zamknięcie wyrażenia (`}`).
- **L28:** Definicja funkcji/metody `_mode_block`, zwraca `str`.
- **L29:** (w `_mode_block`) Przypisanie `lang` ← `language if language in _MODE_DELTA else "pl"`.
- **L30:** (w `_mode_block`) Przypisanie `mapping` ← `_MODE_DELTA[lang]`.
- **L31:** (w `_mode_block`) Zwraca: `mapping.get(mode, mapping["debug"])`.
- **L34:** Definicja funkcji/metody `format_code_context_block`, zwraca `str`.
- **L35:** (w `format_code_context_block`) Przypisanie `en` ← `language == "en"`.
- **L36:** (w `format_code_context_block`) Przypisanie `parts: list[str]` ← `[]`.
- **L37:** (w `format_code_context_block`) Warunek `if` — gdy `ctx.workspace_root`.
- **L38–L40:** (w `format_code_context_block`) Wyrażenie wieloliniowe — L38: Wykonuje: `parts.append(`. | L39: Wykonuje: `f"{'Workspace root' if en else 'Katalog workspace'}: {ctx.workspace_root}"`. | L40: Zamknięcie wyrażenia (`)`).
- **L41:** (w `format_code_context_block`) Wykonuje: `parts.append(f"{'File' if en else 'Plik'}: {ctx.current_file_name}")`.
- **L42:** (w `format_code_context_block`) Wykonuje: `parts.append(f"{'Code' if en else 'Kod'}:\n```\n{ctx.current_code}\n```")`.
- **L43:** (w `format_code_context_block`) Warunek `if` — gdy `ctx.selection`.
- **L44:** (w `format_code_context_block`) Przypisanie `sel_text` ← `ctx.selection.text or ""`.
- **L45–L49:** (w `format_code_context_block`) Wyrażenie wieloliniowe — L45: Przypisanie `label` ← `(`. | L46: Wykonuje: `f"Selection lines {ctx.selection.start_line}-{ctx.selection.end_line}"`. | L47: Warunek `if` — gdy `en`. | L48: Wykonuje: `else f"Zaznaczenie linie {ctx.selection.start_line}-{ctx.selection.end_line}"`. | L49: Zamknięcie wyrażenia (`)`).
- **L50:** (w `format_code_context_block`) Wykonuje: `parts.append(f"{label}:\n```\n{sel_text}\n```")`.
- **L51:** (w `format_code_context_block`) Warunek `if` — gdy `ctx.diagnostics`.
- **L52:** (w `format_code_context_block`) Przypisanie `diag_lines` ← `[]`.
- **L53:** (w `format_code_context_block`) Pętla `for` po `d in ctx.diagnostics[:20]`.
- **L54:** (w `format_code_context_block`) Przypisanie `loc` ← `f"{d.file or ctx.current_file_name}:{d.line or '?'}"`.
- **L55:** (w `format_code_context_block`) Wykonuje: `diag_lines.append(f"- [{d.severity}] {loc} {d.message}")`.
- **L56–L58:** (w `format_code_context_block`) Wyrażenie wieloliniowe — L56: Wykonuje: `parts.append(`. | L57: Wykonuje: `("Diagnostics" if en else "Diagnostyki") + ":\n" + "\n".join(diag_lines)`. | L58: Zamknięcie wyrażenia (`)`).
- **L59:** (w `format_code_context_block`) Warunek `if` — gdy `ctx.open_files`.
- **L60–L62:** (w `format_code_context_block`) Wyrażenie wieloliniowe — L60: Przypisanie `extras` ← `[`. | L61: Wykonuje: `f"### {f.path}\n```\n{f.content[:1500]}\n```" for f in ctx.open_files[:5]`. | L62: Zamknięcie wyrażenia (`]`).
- **L63–L67:** (w `format_code_context_block`) Wyrażenie wieloliniowe — L63: Wykonuje: `parts.append(`. | L64: Wykonuje: `("Other open files" if en else "Inne otwarte pliki")`. | L65: Wykonuje: `+ ":\n"`. | L66: Wykonuje: `+ "\n".join(extras)`. | L67: Zamknięcie wyrażenia (`)`).
- **L68:** (w `format_code_context_block`) Przypisanie `logs` ← `ctx.error_logs or ("None" if en else "Brak")`.
- **L69:** (w `format_code_context_block`) Wykonuje: `parts.append(f"{'Error logs' if en else 'Logi błędów'}: {logs}")`.
- **L70:** (w `format_code_context_block`) Zwraca: `"\n".join(parts)`.
- **L73:** Definicja funkcji/metody `generation_params`, zwraca `dict`.
- **L74:** (w `generation_params`) Warunek `if` — gdy `mode == "theory"`.
- **L75:** (w `generation_params`) Zwraca: `{"temperature": 0.5, "max_tokens": 280}`.
- **L76:** (w `generation_params`) Warunek `if` — gdy `mode == "review"`.
- **L77:** (w `generation_params`) Zwraca: `{"temperature": 0.4, "max_tokens": 400}`.
- **L78:** (w `generation_params`) Zwraca: `{"temperature": 0.7, "max_tokens": 350}`.
- **L81:** Definicja funkcji/metody `build_system_prompt`, zwraca `str`.
- **L82:** (w `build_system_prompt`) Przypisanie `config` ← `conversation.config`.
- **L83:** (w `build_system_prompt`) Przypisanie `lang` ← `config.language`.
- **L84:** (w `build_system_prompt`) Przypisanie `rules` ← `"\n".join(f"- {rule}" for rule in config.agentBehavior.strictRules)`.
- **L85–L90:** (w `build_system_prompt`) Wyrażenie wieloliniowe — L85: Przypisanie `materials` ← `"\n".join(`. | L86: Wykonuje: `f"- {m.title} ({m.url})"`. | L87: Wykonuje: `+ (f" @{m.timestamp}" if m.timestamp else "")`. | L88: Wykonuje: `+ (f" p.{m.page}" if m.page else "")`. | L89: Pętla `for` po `m in config.learningContext.referenceMaterials`. | L90: Zamknięcie wyrażenia (`)`).
- **L91:** (w `build_system_prompt`) Przypisanie `criteria` ← `config.evaluationCriteria or []`.
- **L92:** (w `build_system_prompt`) Warunek `if` — gdy `criteria`.
- **L93:** (w `build_system_prompt`) Przypisanie `criteria_block` ← `"\n".join(f"- {c}" for c in criteria)`.
- **L94:** (w `build_system_prompt`) Warunek `elif` — gdy `lang == "en"`.
- **L95–L97:** (w `build_system_prompt`) Wyrażenie wieloliniowe — L95: Przypisanie `criteria_block` ← `(`. | L96: Wykonuje: `"- Clarity of the question\n- Use of code context\n- Progress on goals"`. | L97: Zamknięcie wyrażenia (`)`).
- **L98:** (w `build_system_prompt`) Gałąź `else` (pozostałe przypadki).
- **L99–L101:** (w `build_system_prompt`) Wyrażenie wieloliniowe — L99: Przypisanie `criteria_block` ← `(`. | L100: Wykonuje: `"- Jasność pytania\n- Użycie kontekstu kodu\n- Postęp względem celów"`. | L101: Zamknięcie wyrażenia (`)`).
- **L103:** (w `build_system_prompt`) Przypisanie `mode` ← `config.agentBehavior.mode or "debug"`.
- **L104:** (w `build_system_prompt`) Przypisanie `mode_block` ← `_mode_block(lang, mode)`.
- **L106:** (w `build_system_prompt`) Przypisanie `last_user` ← `""`.
- **L107:** (w `build_system_prompt`) Pętla `for` po `m in reversed(conversation.messages)`.
- **L108:** (w `build_system_prompt`) Warunek `if` — gdy `m.get("role") == "user"`.
- **L109:** (w `build_system_prompt`) Przypisanie `last_user` ← `str(m.get("content") or "")`.
- **L110:** (w `build_system_prompt`) Przerywa pętlę (`break`).
- **L111–L118:** (w `build_system_prompt`) Wyrażenie wieloliniowe — L111: Przypisanie `recall_intent` ← `bool(`. | L112: Wykonuje: `conversation.pinned_identifiers`. | L113: Wykonuje: `and re.search(`. | L114: Element listy/argumentów: `r"(nazw[aeę]|zmienn|identifier|variable|wcze[sś]niej|poda[łl]em|remember|earlier)",`. | L115: Element listy/argumentów: `last_user,`. | L116: Element listy/argumentów: `re.IGNORECASE,`. | L117: Zamknięcie wyrażenia (`)`). | L118: Zamknięcie wyrażenia (`)`).
- **L120–L123:** (w `build_system_prompt`) Wyrażenie wieloliniowe — L120: Przypisanie `frustrated` ← `(`. | L121: Przypisanie `consecutive_low_scores(conversation.prompt_scores) >` ← `FRUSTRATION_STREAK`. | L122: Wykonuje: `and not recall_intent`. | L123: Zamknięcie wyrażenia (`)`).
- **L124:** (w `build_system_prompt`) Warunek `if` — gdy `frustrated`.
- **L125–L129:** (w `build_system_prompt`) Wyrażenie wieloliniowe — L125: Przypisanie `frustration` ← `(`. | L126: Wykonuje: `"Student is stuck: give one direct, simple technical hint; ease Socratic pressure."`. | L127: Warunek `if` — gdy `lang == "en"`. | L128: Wykonuje: `else "Student utknął: podaj jedną prostą, bezpośrednią wskazówkę; złagodź rygor sokratyczny."`. | L129: Zamknięcie wyrażenia (`)`).
- **L130:** (w `build_system_prompt`) Gałąź `else` (pozostałe przypadki).
- **L131:** (w `build_system_prompt`) Przypisanie `frustration` ← `""`.
- **L133:** (w `build_system_prompt`) Warunek `if` — gdy `conversation.pinned_identifiers`.
- **L134:** (w `build_system_prompt`) Przypisanie `joined` ← `", ".join(conversation.pinned_identifiers)`.
- **L135–L139:** (w `build_system_prompt`) Wyrażenie wieloliniowe — L135: Przypisanie `pin_rule` ← `(`. | L136: Wykonuje: `f"Pinned identifiers from the student (use verbatim when relevant): {joined}"`. | L137: Warunek `if` — gdy `lang == "en"`. | L138: Wykonuje: `else f"Zachowane identyfikatory studenta (używaj dosłownie, gdy pasują): {joined}"`. | L139: Zamknięcie wyrażenia (`)`).
- **L140:** (w `build_system_prompt`) Gałąź `else` (pozostałe przypadki).
- **L141:** (w `build_system_prompt`) Przypisanie `pin_rule` ← `""`.
- **L143:** (w `build_system_prompt`) Warunek `if` — gdy `lang == "en"`.
- **L144:** (w `build_system_prompt`) Zwraca: `f"""You are a programming mentor ({config.agentBehavior.persona.role}), tone: {config.agentBehavior.persona.t…`.
- **L145:** (w `build_system_prompt`) Wykonuje: `{mode_block}`.
- **L147:** (w `build_system_prompt`) Wykonuje: `Rules:`.
- **L148:** (w `build_system_prompt`) Wykonuje: `{rules}`.
- **L149:** (w `build_system_prompt`) Przypisanie `Refuse full solution dumps; set penalty_applied` ← `true if they demand complete code. Annotation names (e.g. @RestContro…`.
- **L151:** (w `build_system_prompt`) Wykonuje: `Score prompt_score (1–10) by:`.
- **L152:** (w `build_system_prompt`) Wykonuje: `{criteria_block}`.
- **L153:** (w `build_system_prompt`) Wykonuje: `Vague stuck messages without a concrete error/code detail ("doesn't work", "still broken") → score ≤ 3. Polit…`.
- **L155:** (w `build_system_prompt`) Wykonuje: `Pedagogy: theory → explain directly; small talk → brief and kind; coding stuck → Socratic questions. Reuse ex…`.
- **L156:** (w `build_system_prompt`) Wykonuje: `{frustration}`.
- **L157:** (w `build_system_prompt`) Wykonuje: `{pin_rule}`.
- **L159:** (w `build_system_prompt`) Wykonuje: `Materials:`.
- **L160:** (w `build_system_prompt`) Wykonuje: `{materials}`.
- **L162:** (w `build_system_prompt`) Wykonuje: `Respond ONLY with JSON:`.
- **L163:** (w `build_system_prompt`) Wykonuje: `{{"answer":"...","prompt_score":1-10,"prompt_feedback":"...","penalty_applied":false,"suggested_next_step":".…`.
- **L164:** (w `build_system_prompt`) Wykonuje: `Language: English only.`.
- **L165–L167:** Docstring / wieloliniowy literał tekstowy (otwarcie w L165, zamknięcie w L167).
- **L168:** (w `build_system_prompt`) Wykonuje: `{mode_block}`.
- **L170:** (w `build_system_prompt`) Wykonuje: `Zasady:`.
- **L171:** (w `build_system_prompt`) Wykonuje: `{rules}`.
- **L172:** (w `build_system_prompt`) Przypisanie `Odmawiaj gotowych rozwiązań; penalty_applied` ← `true przy żądaniu pełnego kodu. Nazwy adnotacji (np. @RestController)…`.
- **L174:** (w `build_system_prompt`) Wykonuje: `Oceń prompt_score (1–10) według:`.
- **L175:** (w `build_system_prompt`) Wykonuje: `{criteria_block}`.
- **L176:** (w `build_system_prompt`) Wykonuje: `Niejasne „nie działa” / „dalej źle” bez konkretnego błędu lub fragmentu kodu → score ≤ 3. Same uprzejme small…`.
- **L178:** (w `build_system_prompt`) Wykonuje: `Pedagogika: teoria → wyjaśnij wprost; luźna rozmowa → krótko i życzliwie; problem z kodem → pytania naprowadz…`.
- **L179:** (w `build_system_prompt`) Wykonuje: `{frustration}`.
- **L180:** (w `build_system_prompt`) Wykonuje: `{pin_rule}`.
- **L182:** (w `build_system_prompt`) Wykonuje: `Materiały:`.
- **L183:** (w `build_system_prompt`) Wykonuje: `{materials}`.
- **L185:** (w `build_system_prompt`) Wykonuje: `Odpowiedz WYŁĄCZNIE JSON-em:`.
- **L186:** (w `build_system_prompt`) Wykonuje: `{{"answer":"...","prompt_score":1-10,"prompt_feedback":"...","penalty_applied":false,"suggested_next_step":".…`.
- **L187:** (w `build_system_prompt`) Wykonuje: `Język: wyłącznie polski.`.
- **L188–L188:** Docstring / wieloliniowy literał tekstowy (otwarcie w L188, zamknięcie w L188).

<a id="app-application-stream-py"></a>
## `app/application/stream.py`
Streaming NDJSON tokenów odpowiedzi LLM z finalnym payloadem.

Liczba linii: **154**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L5:** Importy — L3: `import json`; L4: `import logging`; L5: `from typing import TYPE_CHECKING`.
- **L7–L13:** Importy — L7: `from app.api.schemas.requests import MessageRequest`; L8: `from app.application.response_pipeline import (`; L9: `IncrementalAnswerExtractor,`; L10: `llm_error_fallback,`; L11: `process_model_response,`; L12: `)`; L13: `from app.core.metrics import metrics`.
- **L15:** Warunek `if` — gdy `TYPE_CHECKING`.
- **L16–L16:** Importy — L16: `from app.application.container import AppContainer`.
- **L18:** Przypisanie `STREAM_CHUNK_SIZE` ← `40`.
- **L19:** Przypisanie `logger` ← `logging.getLogger(__name__)`.
- **L22:** Definicja klasy `StreamService`.
- **L23:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L24:** (w `StreamService`) Przypisanie `self._app` ← `app`.
- **L26–L28:** (w `StreamService`) Wyrażenie wieloliniowe — L26: Definicja funkcji/metody `?`. | L27: Wykonuje: `self, conversation_id: str, request: MessageRequest, message_id: str`. | L28: Wykonuje: `):`.
- **L29:** Docstring: Live NDJSON: token deltas as the model writes ``answer``, then a final payload.
- **L30:** (w `StreamService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L31:** (w `StreamService`) Wykonuje: `self._app.sessions.ensure_prelab_passed(conversation)`.
- **L32:** (w `StreamService`) Wykonuje: `self._app.sessions.ensure_token_budget(conversation)`.
- **L34:** (w `StreamService`) Przypisanie `lang` ← `conversation.config.language`.
- **L35:** (w `StreamService`) Przypisanie `was_frustrated` ← `conversation.is_frustrated`.
- **L37–L39:** (w `StreamService`) Wyrażenie wieloliniowe — L37: Przypisanie `prior` ← `self._app.sessions.lookup_idempotent(`. | L38: Wykonuje: `conversation_id, request.client_message_id`. | L39: Zamknięcie wyrażenia (`)`).
- **L40:** (w `StreamService`) Warunek `if` — gdy `prior`.
- **L41:** (w `StreamService`) Wykonuje: `self._app.chat._track_result_metrics(prior)`.
- **L42:** (w `StreamService`) Blok strukturalny: `async for line in self._ndjson_stream_result(prior):`.
- **L43:** (w `StreamService`) Yield (strumień/generator): `line`.
- **L44:** (w `StreamService`) Zwraca `None`.
- **L46–L48:** (w `StreamService`) Wyrażenie wieloliniowe — L46: Przypisanie `cached` ← `self._app.chat._try_cache(`. | L47: Wykonuje: `conversation, conversation_id, request, message_id`. | L48: Zamknięcie wyrażenia (`)`).
- **L49:** (w `StreamService`) Warunek `if` — gdy `cached`.
- **L50–L52:** (w `StreamService`) Wyrażenie wieloliniowe — L50: Przypisanie `cached` ← `self._app.sessions.store_idempotent(`. | L51: Wykonuje: `conversation_id, request.client_message_id, cached`. | L52: Zamknięcie wyrażenia (`)`).
- **L53:** (w `StreamService`) Wykonuje: `self._app.chat._track_result_metrics(cached)`.
- **L54:** (w `StreamService`) Blok strukturalny: `async for line in self._ndjson_stream_result(cached):`.
- **L55:** (w `StreamService`) Yield (strumień/generator): `line`.
- **L56:** (w `StreamService`) Zwraca `None`.
- **L58–L60:** (w `StreamService`) Wyrażenie wieloliniowe — L58: Przypisanie `chat_messages, code_changed, sources` ← `await self._app.chat._prepare_chat_context(`. | L59: Wykonuje: `conversation_id, request`. | L60: Zamknięcie wyrażenia (`)`).
- **L61:** (w `StreamService`) Przypisanie `gen` ← `self._app.chat._gen_kwargs(conversation)`.
- **L63:** (w `StreamService`) Przypisanie `full_raw_response` ← `""`.
- **L64:** (w `StreamService`) Przypisanie `usage` ← `None`.
- **L65:** (w `StreamService`) Przypisanie `extractor` ← `IncrementalAnswerExtractor()`.
- **L67:** Definicja asynchronicznej funkcji/metody `_emit_live_from_stream`.
- **L68:** (w `StreamService`) Deklaracja zasięgu: `nonlocal full_raw_response, usage`.
- **L69:** (w `StreamService`) Blok strukturalny: `async for chunk in response_iter:`.
- **L70:** (w `StreamService`) Warunek `if` — gdy `getattr(chunk, "usage", None)`.
- **L71:** (w `StreamService`) Przypisanie `usage` ← `chunk.usage`.
- **L72:** (w `StreamService`) Warunek `if` — gdy `not chunk.choices`.
- **L73:** (w `StreamService`) Przechodzi do kolejnej iteracji pętli (`continue`).
- **L74:** (w `StreamService`) Przypisanie `piece` ← `chunk.choices[0].delta.content or ""`.
- **L75:** (w `StreamService`) Warunek `if` — gdy `not piece`.
- **L76:** (w `StreamService`) Przechodzi do kolejnej iteracji pętli (`continue`).
- **L77:** (w `StreamService`) Przypisanie `full_raw_response +` ← `piece`.
- **L78:** (w `StreamService`) Przypisanie `delta` ← `extractor.feed(piece)`.
- **L79:** (w `StreamService`) Warunek `if` — gdy `delta`.
- **L80–L82:** (w `StreamService`) Wyrażenie wieloliniowe — L80: Yield (strumień/generator): `json.dumps(`. | L81: Przypisanie `{"type": "token", "text": delta}, ensure_ascii` ← `False`. | L82: Wykonuje: `) + "\n"`.
- **L84:** (w `StreamService`) Blok `try` — chroniony kod, potem except/finally.
- **L85–L95:** (w `StreamService`) Wyrażenie wieloliniowe — L85: Przypisanie `response` ← `await self._app.client.chat.completions.create(`. | L86: Przypisanie `model` ← `self._app.llm.model_for(conversation),`. | L87: Przypisanie `messages` ← `chat_messages,`. | L88: Przypisanie `temperature` ← `gen["temperature"],`. | L89: Przypisanie `presence_penalty` ← `gen["presence_penalty"],`. | L90: Przypisanie `frequency_penalty` ← `gen["frequency_penalty"],`. | L91: Przypisanie `max_tokens` ← `gen["max_tokens"],`. | L92: Przypisanie `stream` ← `True,`. | L93: Przypisanie `stream_options` ← `{"include_usage": True},`. | L94: Przypisanie `response_format` ← `gen["response_format"],`. | L95: Zamknięcie wyrażenia (`)`).
- **L96:** (w `StreamService`) Blok strukturalny: `async for line in _emit_live_from_stream(response):`.
- **L97:** (w `StreamService`) Yield (strumień/generator): `line`.
- **L98:** (w `StreamService`) Przechwytuje wyjątek `TypeError`.
- **L99:** (w `StreamService`) Blok `try` — chroniony kod, potem except/finally.
- **L100–L109:** (w `StreamService`) Wyrażenie wieloliniowe — L100: Przypisanie `response` ← `await self._app.client.chat.completions.create(`. | L101: Przypisanie `model` ← `self._app.llm.model_for(conversation),`. | L102: Przypisanie `messages` ← `chat_messages,`. | L103: Przypisanie `temperature` ← `gen["temperature"],`. | L104: Przypisanie `presence_penalty` ← `gen["presence_penalty"],`. | L105: Przypisanie `frequency_penalty` ← `gen["frequency_penalty"],`. | L106: Przypisanie `max_tokens` ← `gen["max_tokens"],`. | L107: Przypisanie `stream` ← `True,`. | L108: Przypisanie `response_format` ← `gen["response_format"],`. | L109: Zamknięcie wyrażenia (`)`).
- **L110:** (w `StreamService`) Blok strukturalny: `async for line in _emit_live_from_stream(response):`.
- **L111:** (w `StreamService`) Yield (strumień/generator): `line`.
- **L112:** (w `StreamService`) Przechwytuje wyjątek `Exception as e`.
- **L113:** (w `StreamService`) Wykonuje: `metrics.inc("llm_errors")`.
- **L114:** (w `StreamService`) Log: `logger.error("Stream LLM error: %s", e)`.
- **L115:** (w `StreamService`) Przypisanie `fallback` ← `llm_error_fallback(message_id, lang)`.
- **L116:** (w `StreamService`) Blok strukturalny: `async for line in self._ndjson_stream_result(fallback):`.
- **L117:** (w `StreamService`) Yield (strumień/generator): `line`.
- **L118:** (w `StreamService`) Zwraca `None`.
- **L119:** (w `StreamService`) Przechwytuje wyjątek `Exception as e`.
- **L120:** (w `StreamService`) Wykonuje: `metrics.inc("llm_errors")`.
- **L121:** (w `StreamService`) Log: `logger.error("Stream LLM error: %s", e)`.
- **L122:** (w `StreamService`) Przypisanie `fallback` ← `llm_error_fallback(message_id, lang)`.
- **L123:** (w `StreamService`) Blok strukturalny: `async for line in self._ndjson_stream_result(fallback):`.
- **L124:** (w `StreamService`) Yield (strumień/generator): `line`.
- **L125:** (w `StreamService`) Zwraca `None`.
- **L127:** (w `StreamService`) Przypisanie `prompt_text` ← `"\n".join(str(m.get("content") or "") for m in chat_messages)`.
- **L128–L130:** (w `StreamService`) Wyrażenie wieloliniowe — L128: Przypisanie `tokens_used` ← `self._app.llm.tokens_from_usage(`. | L129: Wykonuje: `usage, prompt_text, full_raw_response`. | L130: Zamknięcie wyrażenia (`)`).
- **L131–L139:** (w `StreamService`) Wyrażenie wieloliniowe — L131: Przypisanie `final_result` ← `process_model_response(`. | L132: Element listy/argumentów: `full_raw_response,`. | L133: Element listy/argumentów: `conversation,`. | L134: Przypisanie `message_id` ← `message_id,`. | L135: Przypisanie `tokens_used` ← `tokens_used,`. | L136: Przypisanie `code_changed` ← `code_changed,`. | L137: Przypisanie `was_frustrated` ← `was_frustrated,`. | L138: Przypisanie `sources` ← `sources,`. | L139: Zamknięcie wyrażenia (`)`).
- **L140:** (w `StreamService`) Wykonuje: `self._app.chat.remember_goal_progress(conversation, final_result)`.
- **L141:** (w `StreamService`) Wykonuje: `self._app.chat._save_cache(conversation_id, request, final_result)`.
- **L142–L144:** (w `StreamService`) Wyrażenie wieloliniowe — L142: Przypisanie `final_result` ← `self._app.sessions.store_idempotent(`. | L143: Wykonuje: `conversation_id, request.client_message_id, final_result`. | L144: Zamknięcie wyrażenia (`)`).
- **L145:** (w `StreamService`) Wykonuje: `self._app.chat._track_result_metrics(final_result)`.
- **L146:** (w `StreamService`) Yield (strumień/generator): `json.dumps({"type": "final", **final_result}, ensure_ascii=False) + "\n"`.
- **L148:** Definicja asynchronicznej funkcji/metody `_ndjson_stream_result`.
- **L149:** Docstring: Replay helper for cache / errors (instant fake stream + final).
- **L150:** (w `StreamService`) Przypisanie `answer` ← `str(result.get("answer") or "")`.
- **L151:** (w `StreamService`) Pętla `for` po `i in range(0, len(answer), STREAM_CHUNK_SIZE)`.
- **L152:** (w `StreamService`) Przypisanie `piece` ← `answer[i : i + STREAM_CHUNK_SIZE]`.
- **L153:** (w `StreamService`) Yield (strumień/generator): `json.dumps({"type": "token", "text": piece}, ensure_ascii=False) + "\n"`.
- **L154:** (w `StreamService`) Yield (strumień/generator): `json.dumps({"type": "final", **result}, ensure_ascii=False) + "\n"`.

<a id="app-application-prelab-py"></a>
## `app/application/prelab.py`
Quiz pre-lab: odczyt, submit (słowa kluczowe), generowanie pytań LLM.

Liczba linii: **147**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L4:** Importy — L3: `import json`; L4: `from typing import TYPE_CHECKING`.
- **L6–L7:** Importy — L6: `from app.api.schemas.requests import PreLabSubmitRequest`; L7: `from app.domain.sensei import PreLabConfig, PreLabQuestion`.
- **L9:** Warunek `if` — gdy `TYPE_CHECKING`.
- **L10–L10:** Importy — L10: `from app.application.container import AppContainer`.
- **L13:** Definicja klasy `PrelabService`.
- **L14:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L15:** (w `PrelabService`) Przypisanie `self._app` ← `app`.
- **L17:** Definicja funkcji/metody `get_prelab_public`, zwraca `dict`.
- **L18:** (w `PrelabService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L19:** (w `PrelabService`) Przypisanie `prelab` ← `conversation.config.preLab`.
- **L20:** (w `PrelabService`) Warunek `if` — gdy `not prelab or not prelab.enabled`.
- **L21–L28:** (w `PrelabService`) Wyrażenie wieloliniowe — L21: Zwraca: `{`. | L22: Element listy/argumentów: `"enabled": False,`. | L23: Element listy/argumentów: `"passed": True,`. | L24: Element listy/argumentów: `"questions": [],`. | L25: Element listy/argumentów: `"attempts": 0,`. | L26: Element listy/argumentów: `"max_attempts": None,`. | L27: Element listy/argumentów: `"score": None,`. | L28: Zamknięcie wyrażenia (`}`).
- **L29–L37:** (w `PrelabService`) Wyrażenie wieloliniowe — L29: Zwraca: `{`. | L30: Element listy/argumentów: `"enabled": True,`. | L31: Element listy/argumentów: `"passed": conversation.prelab_passed,`. | L32: Element listy/argumentów: `"questions": [{"id": q.id, "prompt": q.prompt} for q in prelab.questions],`. | L33: Element listy/argumentów: `"attempts": conversation.prelab_attempts,`. | L34: Element listy/argumentów: `"max_attempts": prelab.max_attempts,`. | L35: Element listy/argumentów: `"score": conversation.last_prelab_score,`. | L36: Element listy/argumentów: `"hint_after_fail": prelab.hint_after_fail,`. | L37: Zamknięcie wyrażenia (`}`).
- **L39:** Definicja funkcji/metody `submit_prelab`, zwraca `dict`.
- **L40:** (w `PrelabService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L41:** (w `PrelabService`) Przypisanie `prelab` ← `conversation.config.preLab`.
- **L42:** (w `PrelabService`) Warunek `if` — gdy `not prelab or not prelab.enabled`.
- **L43:** (w `PrelabService`) Przypisanie `conversation.prelab_passed` ← `True`.
- **L44:** (w `PrelabService`) Zwraca: `{"passed": True, "detail": "Pre-lab not required", "score": 1.0}`.
- **L46–L50:** (w `PrelabService`) Wyrażenie wieloliniowe — L46: Warunek `if` — gdy `(`. | L47: Wykonuje: `prelab.max_attempts is not None`. | L48: Przypisanie `and conversation.prelab_attempts >` ← `prelab.max_attempts`. | L49: Wykonuje: `and not conversation.prelab_passed`. | L50: Wykonuje: `):`.
- **L51–L59:** (w `PrelabService`) Wyrażenie wieloliniowe — L51: Zwraca: `{`. | L52: Element listy/argumentów: `"passed": False,`. | L53: Element listy/argumentów: `"detail": "max_attempts exceeded",`. | L54: Element listy/argumentów: `"failed_ids": [],`. | L55: Element listy/argumentów: `"score": conversation.last_prelab_score or 0.0,`. | L56: Element listy/argumentów: `"attempts": conversation.prelab_attempts,`. | L57: Element listy/argumentów: `"max_attempts": prelab.max_attempts,`. | L58: Element listy/argumentów: `"hint_after_fail": prelab.hint_after_fail,`. | L59: Zamknięcie wyrażenia (`}`).
- **L61:** (w `PrelabService`) Przypisanie `conversation.prelab_attempts +` ← `1`.
- **L62:** (w `PrelabService`) Przypisanie `answers_by_id` ← `{a.id: a.answer.lower() for a in payload.answers}`.
- **L63:** (w `PrelabService`) Przypisanie `failures: list[str]` ← `[]`.
- **L64:** (w `PrelabService`) Przypisanie `matched` ← `0`.
- **L65:** (w `PrelabService`) Przypisanie `total` ← `len(prelab.questions) or 1`.
- **L66:** (w `PrelabService`) Pętla `for` po `q in prelab.questions`.
- **L67:** (w `PrelabService`) Przypisanie `student_ans` ← `answers_by_id.get(q.id, "")`.
- **L68:** (w `PrelabService`) Warunek `if` — gdy `not q.expected_keywords`.
- **L69:** (w `PrelabService`) Przypisanie `ok` ← `bool(student_ans.strip())`.
- **L70:** (w `PrelabService`) Gałąź `else` (pozostałe przypadki).
- **L71:** (w `PrelabService`) Przypisanie `ok` ← `any(kw.lower() in student_ans for kw in q.expected_keywords)`.
- **L72:** (w `PrelabService`) Warunek `if` — gdy `ok`.
- **L73:** (w `PrelabService`) Przypisanie `matched +` ← `1`.
- **L74:** (w `PrelabService`) Gałąź `else` (pozostałe przypadki).
- **L75:** (w `PrelabService`) Wykonuje: `failures.append(q.id)`.
- **L77:** (w `PrelabService`) Przypisanie `score` ← `round(matched / total, 3)`.
- **L78:** (w `PrelabService`) Przypisanie `conversation.last_prelab_score` ← `score`.
- **L79:** (w `PrelabService`) Przypisanie `conversation.prelab_passed` ← `len(failures) == 0`.
- **L80:** (w `PrelabService`) Wykonuje: `conversation.touch()`.
- **L81–L95:** (w `PrelabService`) Wyrażenie wieloliniowe — L81: Zwraca: `{`. | L82: Element listy/argumentów: `"passed": conversation.prelab_passed,`. | L83: Wykonuje: `"detail": (`. | L84: Wykonuje: `"OK"`. | L85: Warunek `if` — gdy `conversation.prelab_passed`. | L86: Wykonuje: `else f"Failed questions: {', '.join(failures)}"`. | L87: Element listy/argumentów: `),`. | L88: Element listy/argumentów: `"failed_ids": failures,`. | L89: Element listy/argumentów: `"score": score,`. | L90: Element listy/argumentów: `"attempts": conversation.prelab_attempts,`. | L91: Element listy/argumentów: `"max_attempts": prelab.max_attempts,`. | L92: Wykonuje: `"hint_after_fail": (`. | L93: Wykonuje: `None if conversation.prelab_passed else prelab.hint_after_fail`. | L94: Element listy/argumentów: `),`. | L95: Zamknięcie wyrażenia (`}`).
- **L97:** Definicja asynchronicznej funkcji/metody `generate_prelab`, zwraca `dict`.
- **L98:** (w `PrelabService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L99–L101:** (w `PrelabService`) Wyrażenie wieloliniowe — L99: Przypisanie `rag_text, _` ← `self._app.rag.retrieve_context(`. | L100: Wykonuje: `conversation_id, conversation.problem`. | L101: Zamknięcie wyrażenia (`)`).
- **L102–L105:** (w `PrelabService`) Wyrażenie wieloliniowe — L102: Przypisanie `materials` ← `"\n".join(`. | L103: Wykonuje: `f"- {m.title}: {m.url}"`. | L104: Pętla `for` po `m in conversation.config.learningContext.referenceMaterials`. | L105: Zamknięcie wyrażenia (`)`).
- **L106:** (w `PrelabService`) Przypisanie `lang` ← `conversation.config.language`.
- **L107:** (w `PrelabService`) Przypisanie `prompt` ← `f"""`.
- **L108:** (w `PrelabService`) Wykonuje: `Generate exactly 3 short pre-lab quiz questions for students before coding.`.
- **L109:** (w `PrelabService`) Wykonuje: `Assignment: {conversation.problem}`.
- **L110:** (w `PrelabService`) Wykonuje: `Materials:`.
- **L111:** (w `PrelabService`) Wykonuje: `{materials}`.
- **L112:** (w `PrelabService`) Wykonuje: `RAG excerpts:`.
- **L113:** (w `PrelabService`) Wykonuje: `{rag_text[:2500]}`.
- **L115:** (w `PrelabService`) Wykonuje: `Return JSON:`.
- **L116–L120:** (w `PrelabService`) Wyrażenie wieloliniowe — L116: Wykonuje: `{{`. | L117: Wykonuje: `"questions": [`. | L118: Wykonuje: `{{"id": "q1", "prompt": "...", "expected_keywords": ["kw1", "kw2"]}}`. | L119: Zamknięcie wyrażenia (`]`). | L120: Wykonuje: `}}`.
- **L121:** (w `PrelabService`) Przypisanie `Language of prompts: {"English" if lang` ← `= "en" else "Polish"}.`.
- **L122–L147:** Docstring / wieloliniowy literał tekstowy (otwarcie w L122, zamknięcie w L147).

<a id="app-application-review-py"></a>
## `app/application/review.py`
Sokratyczny review kodu bez pełnych patchy.

Liczba linii: **95**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L4:** Importy — L3: `import json`; L4: `from typing import TYPE_CHECKING`.
- **L6–L9:** Importy — L6: `from app.api.schemas.requests import ReviewRequest`; L7: `from app.application.prompts import format_code_context_block`; L8: `from app.application.response_pipeline import contains_revealed_code`; L9: `from app.core.metrics import metrics`.
- **L11:** Warunek `if` — gdy `TYPE_CHECKING`.
- **L12–L12:** Importy — L12: `from app.application.container import AppContainer`.
- **L15:** Definicja klasy `ReviewService`.
- **L16:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L17:** (w `ReviewService`) Przypisanie `self._app` ← `app`.
- **L19:** Definicja asynchronicznej funkcji/metody `review_code`, zwraca `dict`.
- **L20:** (w `ReviewService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L21:** (w `ReviewService`) Wykonuje: `self._app.sessions.ensure_prelab_passed(conversation)`.
- **L22:** (w `ReviewService`) Przypisanie `lang` ← `conversation.config.language`.
- **L23:** (w `ReviewService`) Przypisanie `ctx` ← `format_code_context_block(payload.code_context, language=lang)`.
- **L24:** (w `ReviewService`) Przypisanie `focus` ← `payload.focus or ""`.
- **L25:** (w `ReviewService`) Przypisanie `prompt` ← `f"""`.
- **L26:** (w `ReviewService`) Wykonuje: `You are a Socratic code reviewer. Do NOT provide a full patch or complete solution.`.
- **L27:** (w `ReviewService`) Przypisanie `Language: {"English" if lang` ← `= "en" else "Polish"}.`.
- **L28:** (w `ReviewService`) Wykonuje: `Assignment: {conversation.problem}`.
- **L29:** (w `ReviewService`) Wykonuje: `Focus: {focus}`.
- **L30:** (w `ReviewService`) Wykonuje: `Student context:`.
- **L31:** (w `ReviewService`) Wykonuje: `{ctx}`.
- **L33:** (w `ReviewService`) Wykonuje: `Return JSON:`.
- **L34–L45:** (w `ReviewService`) Wyrażenie wieloliniowe — L34: Wykonuje: `{{`. | L35: Wykonuje: `"findings": [`. | L36: Wykonuje: `{{`. | L37: Element listy/argumentów: `"severity": "error|warning|info",`. | L38: Element listy/argumentów: `"message": "what looks wrong conceptually",`. | L39: Element listy/argumentów: `"socratic_question": "guiding question",`. | L40: Element listy/argumentów: `"file": "optional path",`. | L41: Wykonuje: `"line": null`. | L42: Wykonuje: `}}`. | L43: Element listy/argumentów: `],`. | L44: Wykonuje: `"suggested_next_step": "one next action"`. | L45: Wykonuje: `}}`.
- **L46–L95:** Docstring / wieloliniowy literał tekstowy (otwarcie w L46, zamknięcie w L95).

<a id="app-application-summary-py"></a>
## `app/application/summary.py`
Podsumowanie sesji dla wykładowcy (LLM JSON).

Liczba linii: **92**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L5:** Importy — L3: `import json`; L4: `import logging`; L5: `from typing import TYPE_CHECKING`.
- **L7:** Warunek `if` — gdy `TYPE_CHECKING`.
- **L8–L8:** Importy — L8: `from app.application.container import AppContainer`.
- **L10:** Przypisanie `logger` ← `logging.getLogger(__name__)`.
- **L13:** Definicja klasy `SummaryService`.
- **L14:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L15:** (w `SummaryService`) Przypisanie `self._app` ← `app`.
- **L17:** Definicja asynchronicznej funkcji/metody `generate_summary`, zwraca `dict`.
- **L18:** (w `SummaryService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L19:** (w `SummaryService`) Wykonuje: `conversation.touch()`.
- **L21–L23:** (w `SummaryService`) Wyrażenie wieloliniowe — L21: Przypisanie `history_text` ← `"\n".join(`. | L22: Wykonuje: `f"{m['role']}: {m['content']}" for m in conversation.messages`. | L23: Zamknięcie wyrażenia (`)`).
- **L24:** (w `SummaryService`) Przypisanie `scores` ← `conversation.prompt_scores`.
- **L25:** (w `SummaryService`) Przypisanie `avg_score` ← `sum(scores) / len(scores) if scores else 0`.
- **L26:** (w `SummaryService`) Przypisanie `lang` ← `conversation.config.language`.
- **L27:** (w `SummaryService`) Przypisanie `criteria` ← `conversation.config.evaluationCriteria`.
- **L28–L39:** (w `SummaryService`) Wyrażenie wieloliniowe — L28: Przypisanie `events_summary` ← `{`. | L29: Wykonuje: `"copy_blocked": sum(`. | L30: Przypisanie `1 for e in conversation.ide_events if e.get("type")` ← `= "copy_blocked"`. | L31: Element listy/argumentów: `),`. | L32: Wykonuje: `"paste_attempt": sum(`. | L33: Przypisanie `1 for e in conversation.ide_events if e.get("type")` ← `= "paste_attempt"`. | L34: Element listy/argumentów: `),`. | L35: Wykonuje: `"file_opened": sum(`. | L36: Przypisanie `1 for e in conversation.ide_events if e.get("type")` ← `= "file_opened"`. | L37: Element listy/argumentów: `),`. | L38: Element listy/argumentów: `"reveals": conversation.reveal_count,`. | L39: Zamknięcie wyrażenia (`}`).
- **L41:** (w `SummaryService`) Przypisanie `feedbacks` ← `[]`.
- **L42:** (w `SummaryService`) Pętla `for` po `m in conversation.messages`.
- **L43:** (w `SummaryService`) Warunek `if` — gdy `m.get("role") == "assistant" and "student_feedback" in m`.
- **L44–L47:** (w `SummaryService`) Wyrażenie wieloliniowe — L44: Wykonuje: `feedbacks.append(`. | L45: Przypisanie `f"rating` ← `{m['student_feedback']['rating']}, "`. | L46: Przypisanie `f"comment` ← `{m['student_feedback'].get('comment', '')}"`. | L47: Zamknięcie wyrażenia (`)`).
- **L49–L53:** (w `SummaryService`) Wyrażenie wieloliniowe — L49: Przypisanie `criteria_text` ← `(`. | L50: Wykonuje: `"\n".join(f"- {c}" for c in criteria)`. | L51: Warunek `if` — gdy `criteria`. | L52: Wykonuje: `else "- Clarity, code-context use, progress on goals"`. | L53: Zamknięcie wyrażenia (`)`).
- **L54:** (w `SummaryService`) Przypisanie `feedbacks_text` ← `"\n".join(feedbacks) if feedbacks else "none"`.
- **L56:** (w `SummaryService`) Przypisanie `prompt` ← `f"""`.
- **L57:** (w `SummaryService`) Wykonuje: `Summarize student work for lecturer.`.
- **L58:** (w `SummaryService`) Przypisanie `Language: {"English" if lang` ← `= "en" else "Polish"}.`.
- **L59:** (w `SummaryService`) Wykonuje: `Assignment: {conversation.problem}`.
- **L60:** (w `SummaryService`) Wykonuje: `Criteria:`.
- **L61:** (w `SummaryService`) Wykonuje: `{criteria_text}`.
- **L62:** (w `SummaryService`) Wykonuje: `History:`.
- **L63:** (w `SummaryService`) Wykonuje: `{history_text}`.
- **L64:** (w `SummaryService`) Wykonuje: `Scores: {scores} (avg {avg_score:.2f})`.
- **L65:** (w `SummaryService`) Wykonuje: `Student feedbacks: {feedbacks_text}`.
- **L66:** (w `SummaryService`) Wykonuje: `IDE events: {events_summary}`.
- **L68:** (w `SummaryService`) Wykonuje: `Return JSON with keys:`.
- **L69:** (w `SummaryService`) Element listy/argumentów: `mastery_score, student_actions, agent_evaluation_of_student,`.
- **L70:** (w `SummaryService`) Wykonuje: `student_evaluation_of_agent, professors_summary`.
- **L71–L92:** Docstring / wieloliniowy literał tekstowy (otwarcie w L71, zamknięcie w L92).

<a id="app-application-goals-py"></a>
## `app/application/goals.py`
Ocena postępu celów i powiązanie z checkpointami.

Liczba linii: **76**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L4:** Importy — L3: `import json`; L4: `from typing import TYPE_CHECKING`.
- **L6–L6:** Importy — L6: `from app.core.metrics import metrics`.
- **L8:** Warunek `if` — gdy `TYPE_CHECKING`.
- **L9–L9:** Importy — L9: `from app.application.container import AppContainer`.
- **L12:** Definicja klasy `GoalsService`.
- **L13:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L14:** (w `GoalsService`) Przypisanie `self._app` ← `app`.
- **L16:** Definicja funkcji/metody `get_checkpoints`, zwraca `dict`.
- **L17:** (w `GoalsService`) Zwraca: `self._app.sessions.get_checkpoints(conversation_id)`.
- **L19:** Definicja asynchronicznej funkcji/metody `assess_goals`, zwraca `dict`.
- **L20:** (w `GoalsService`) Przypisanie `conversation` ← `self._app.sessions.get_conversation_or_404(conversation_id)`.
- **L21:** (w `GoalsService`) Wykonuje: `conversation.ensure_goal_progress_defaults()`.
- **L22:** (w `GoalsService`) Przypisanie `lang` ← `conversation.config.language`.
- **L23:** (w `GoalsService`) Przypisanie `goals` ← `conversation.config.learningContext.goals or []`.
- **L24–L27:** (w `GoalsService`) Wyrażenie wieloliniowe — L24: Przypisanie `history_text` ← `"\n".join(`. | L25: Wykonuje: `f"{m.get('role')}: {str(m.get('content') or '')[:400]}"`. | L26: Pętla `for` po `m in conversation.messages[-20:]`. | L27: Zamknięcie wyrażenia (`)`).
- **L28:** (w `GoalsService`) Przypisanie `prompt` ← `f"""`.
- **L29:** (w `GoalsService`) Wykonuje: `Assess student progress against learning goals from conversation history.`.
- **L30:** (w `GoalsService`) Przypisanie `Language: {"English" if lang` ← `= "en" else "Polish"}.`.
- **L31:** (w `GoalsService`) Przypisanie `Goals: {json.dumps(goals, ensure_ascii` ← `False)}`.
- **L32:** (w `GoalsService`) Wykonuje: `History excerpt:`.
- **L33:** (w `GoalsService`) Wykonuje: `{history_text}`.
- **L35:** (w `GoalsService`) Wykonuje: `Return JSON:`.
- **L36:** (w `GoalsService`) Wykonuje: `{{"goal_progress": [{{"goal": "...", "status": "not_started|in_progress|done"}}], "notes": "short"}}`.
- **L37:** (w `GoalsService`) Wykonuje: `Use only the provided goals. No solution code.`.
- **L38–L76:** Docstring / wieloliniowy literał tekstowy (otwarcie w L38, zamknięcie w L76).

<a id="app-application-analytics-py"></a>
## `app/application/analytics.py`
Agregacja korelacji między sesjami (score, rating, kary, IDE).

Liczba linii: **71**.

### Opis linia-po-linii

- **L1–L1:** Importy — L1: `from __future__ import annotations`.
- **L3–L3:** Importy — L3: `from typing import TYPE_CHECKING`.
- **L5:** Warunek `if` — gdy `TYPE_CHECKING`.
- **L6–L6:** Importy — L6: `from app.application.container import AppContainer`.
- **L9:** Definicja klasy `AnalyticsService`.
- **L10:** Definicja funkcji/metody `__init__`, zwraca `None`.
- **L11:** (w `AnalyticsService`) Przypisanie `self._app` ← `app`.
- **L13:** Definicja funkcji/metody `build_correlations`, zwraca `dict`.
- **L14:** (w `AnalyticsService`) Wykonuje: `self._app.sessions.purge_stale_conversations()`.
- **L15:** (w `AnalyticsService`) Przypisanie `rows` ← `[]`.
- **L16:** (w `AnalyticsService`) Pętla `for` po `cid, conv in self._app.conversations.items()`.
- **L17–L21:** (w `AnalyticsService`) Wyrażenie wieloliniowe — L17: Przypisanie `ratings` ← `[`. | L18: Wykonuje: `m["student_feedback"]["rating"]`. | L19: Pętla `for` po `m in conv.messages`. | L20: Warunek `if` — gdy `m.get("role") == "assistant" and "student_feedback" in m`. | L21: Zamknięcie wyrażenia (`]`).
- **L22–L26:** (w `AnalyticsService`) Wyrażenie wieloliniowe — L22: Przypisanie `penalties` ← `sum(`. | L23: Wykonuje: `1`. | L24: Pętla `for` po `m in conv.messages`. | L25: Warunek `if` — gdy `m.get("role") == "assistant" and m.get("penalty_applied")`. | L26: Zamknięcie wyrażenia (`)`).
- **L27–L31:** (w `AnalyticsService`) Wyrażenie wieloliniowe — L27: Przypisanie `avg_prompt` ← `(`. | L28: Wykonuje: `sum(conv.prompt_scores) / len(conv.prompt_scores)`. | L29: Warunek `if` — gdy `conv.prompt_scores`. | L30: Wykonuje: `else 0.0`. | L31: Zamknięcie wyrażenia (`)`).
- **L32:** (w `AnalyticsService`) Przypisanie `avg_rating` ← `sum(ratings) / len(ratings) if ratings else None`.
- **L33–L35:** (w `AnalyticsService`) Wyrażenie wieloliniowe — L33: Przypisanie `copy_blocks` ← `sum(`. | L34: Przypisanie `1 for e in conv.ide_events if e.get("type")` ← `= "copy_blocked"`. | L35: Zamknięcie wyrażenia (`)`).
- **L36–L50:** (w `AnalyticsService`) Wyrażenie wieloliniowe — L36: Wykonuje: `rows.append(`. | L37: Wykonuje: `{`. | L38: Element listy/argumentów: `"conversation_id": cid,`. | L39: Element listy/argumentów: `"turns": len(conv.prompt_scores),`. | L40: Element listy/argumentów: `"avg_prompt_score": round(avg_prompt, 2),`. | L41: Wykonuje: `"avg_student_rating": (`. | L42: Wykonuje: `round(avg_rating, 2) if avg_rating is not None else None`. | L43: Element listy/argumentów: `),`. | L44: Element listy/argumentów: `"student_ratings_count": len(ratings),`. | L45: Element listy/argumentów: `"penalty_count": penalties,`. | L46: Element listy/argumentów: `"copy_blocked_count": copy_blocks,`. | L47: Element listy/argumentów: `"ide_events": len(conv.ide_events),`. | L48: Element listy/argumentów: `"problem": conv.problem[:120],`. | L49: Zamknięcie wyrażenia (`}`). | L50: Zamknięcie wyrażenia (`)`).
- **L52:** (w `AnalyticsService`) Przypisanie `scored` ← `[r for r in rows if r["turns"] > 0]`.
- **L53:** (w `AnalyticsService`) Przypisanie `rated` ← `[r for r in rows if r["avg_student_rating"] is not None]`.
- **L54–L71:** (w `AnalyticsService`) Wyrażenie wieloliniowe — L54: Zwraca: `{`. | L55: Element listy/argumentów: `"conversations": rows,`. | L56: Wykonuje: `"globals": {`. | L57: Element listy/argumentów: `"conversation_count": len(rows),`. | L58: Wykonuje: `"avg_prompt_score": (`. | L59: Wykonuje: `round(sum(r["avg_prompt_score"] for r in scored) / len(scored), 2)`. | L60: Warunek `if` — gdy `scored`. | L61: Wykonuje: `else 0.0`. | L62: Element listy/argumentów: `),`. | L63: Wykonuje: `"avg_student_rating": (`. | L64: Wykonuje: `round(`. | L65: Wykonuje: `sum(r["avg_student_rating"] for r in rated) / len(rated), 2`. | L66: Zamknięcie wyrażenia (`)`). | L67: Warunek `if` — gdy `rated`. | L68: Wykonuje: `else None`. | L69: Element listy/argumentów: `),`. | L70: Element listy/argumentów: `},`. | L71: Zamknięcie wyrażenia (`}`).
