"""Orkiestracja czatu: RAG, bramki pedagogiczne, cache, wywołania LLM i reveal."""

from __future__ import annotations

import difflib
import json
import logging
import uuid
from typing import Any

from app.application.dto import MessageRequest, RevealHintRequest
from app.application.prompts import (
    build_system_prompt,
    format_code_context_block,
    generation_params,
)
from app.application.pedagogy_gates import (
    code_dump_refusal_payload,
    finalize_gate_response,
    is_code_dump_request,
    is_recall_intent,
    pinned_recall_payload,
)
from app.application.response_pipeline import (
    collect_identifier_tokens,
    contains_revealed_code,
    compress_history,
    format_pinned_identifiers_note,
    llm_error_fallback,
    process_model_response,
    rate_limit_fallback,
)
from app.application.llm_errors import (
    call_with_rate_limit_policy,
    is_rate_limit_error,
    is_structured_output_unsupported,
)
from app.application.sessions import SessionService
from app.core.config import MAX_REVEALS_PER_SESSION
from app.core.metrics import metrics
from app.domain.conversation import Conversation, reveal_gate_open
from app.domain.exceptions import RevealNotAllowed
from app.ports import CachePort, LlmPort, RagPort

logger = logging.getLogger(__name__)


class ChatService:
    """Orkiestrator konwersacji dydaktycznej z obsługą RAG, bramek pedagogicznych i cache."""
    def __init__(
        self,
        sessions: SessionService,
        llm: LlmPort,
        rag: RagPort,
        cache: CachePort,
    ) -> None:
        self._sessions = sessions
        self._llm = llm
        self._rag = rag
        self._cache = cache

    def _compute_code_diff(self, old_code: str | None, new_code: str, lang: str) -> tuple[str, bool]:
        """Wylicza zunifikowany diff kodu użytkownika."""
        if not old_code or old_code == new_code:
            return "", False

        diff = "\n".join(
            difflib.unified_diff(
                old_code.splitlines(),
                new_code.splitlines(),
                lineterm="",
            )
        )
        header = (
            "Changes made by student since last prompt:"
            if lang == "en"
            else "Zmiany w kodzie wprowadzone przez studenta od ostatniej porady:"
        )
        return f"\n{header}\n```diff\n{diff}\n```\n", True

    async def prepare_chat_context(
        self,
        conversation_id: str,
        conversation: Conversation,
        request: MessageRequest,
        *,
        append_user: bool = True,
    ) -> tuple[list[dict[str, Any]], bool, list[dict[str, Any]]]:
        """Przygotowuje pełen zestaw wiadomości dla API LLM wraz z RAG i historią."""
        lang = conversation.config.language
        conversation.touch()

        rag_context, sources = self._rag.retrieve_context(
            conversation_id, request.question, lang=lang
        )

        code_diff_text, code_changed = self._compute_code_diff(
            conversation.last_code, request.code_context.current_code, lang
        )
        conversation.last_code = request.code_context.current_code

        context_block = format_code_context_block(request.code_context, language=lang)
        q_label = "Student question" if lang == "en" else "Pytanie studenta"
        user_content = (
            f"{context_block}\n"
            f"{code_diff_text}"
            f"{q_label}: {request.question}\n\n"
            f"{rag_context}"
        )

        if append_user:
            conversation.messages.append({"role": "user", "content": user_content})
            conversation.remember_identifiers(
                collect_identifier_tokens(request.question)
            )

        history_clean = [
            {"role": m["role"], "content": m["content"]} for m in conversation.messages
        ]
        history_compressed = compress_history(
            history_clean,
            language=lang,
            pinned_identifiers=conversation.pinned_identifiers,
        )

        task_label = "Main assignment:" if lang == "en" else "Zadanie główne:"
        chat_messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(conversation)},
            {"role": "system", "content": f"{task_label} {conversation.problem}"},
        ]

        if pinned_note := format_pinned_identifiers_note(conversation.pinned_identifiers, lang):
            chat_messages.append({"role": "system", "content": pinned_note})

        chat_messages.extend(history_compressed)
        return chat_messages, code_changed, sources

    def _persist_and_track(
        self,
        conversation_id: str,
        conversation: Conversation,
        client_message_id: str | None,
        result: dict[str, Any],
        *,
        should_cache: bool = True,
        request: MessageRequest | None = None,
    ) -> dict[str, Any]:
        """Spina zapisywanie stanu, idempotencję, cache i wysyłkę metryk."""
        self.remember_goal_progress(conversation, result)
        self.attach_checkpoint_coaching(conversation, result)

        if should_cache and request:
            self.save_cache(conversation_id, request, result)

        stored = self._sessions.store_idempotent(conversation_id, client_message_id, result)
        self._sessions.save_conversation(conversation_id, conversation)
        self.track_result_metrics(stored)
        return stored

    async def send_message(self, conversation_id: str, request: MessageRequest) -> dict[str, Any]:
        """Główna metoda obsługująca zapytanie studenta."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        self._sessions.ensure_prelab_passed(conversation)
        self._sessions.ensure_token_budget(conversation)

        # 1. Idempotencja
        if prior := self._sessions.lookup_idempotent(conversation_id, request.client_message_id):
            self.track_result_metrics(prior)
            return prior

        # 2. Pamięć podręczna (omijana przy frustracji)
        if cached := self.try_cache(conversation, conversation_id, request):
            return self._persist_and_track(
                conversation_id, conversation, request.client_message_id, cached, should_cache=False
            )

        # 3. Przygotowanie promptu i RAG
        chat_messages, code_changed, sources = await self.prepare_chat_context(
            conversation_id, conversation, request
        )
        message_id = str(uuid.uuid4())

        # 4. Bramka pedagogiczna (Code Dump / Pinned Recall)
        if gated := self.maybe_pedagogy_gate(
            conversation, request, message_id=message_id, code_changed=code_changed, sources=sources
        ):
            return self._persist_and_track(
                conversation_id, conversation, request.client_message_id, gated, should_cache=True, request=request
            )

        # 5. Wywołanie LLM
        gen_kwargs = self.llm_generation_kwargs(conversation)
        model_name = self._llm.model_for(conversation)

        async def _complete_once(model: str):
            try:
                return await self._llm.create_chat_completion(
                    model=model,
                    messages=chat_messages,
                    **gen_kwargs,
                )
            except Exception as first_exc:
                if not is_structured_output_unsupported(first_exc):
                    raise
                logger.warning(
                    "Model nie obsługuje structured outputs — retry bez response_format (%s)",
                    first_exc,
                )
                retry_kwargs = {k: v for k, v in gen_kwargs.items() if k != "response_format"}
                return await self._llm.create_chat_completion(
                    model=model,
                    messages=chat_messages,
                    **retry_kwargs,
                )

        try:
            response, used_model = await call_with_rate_limit_policy(model_name, _complete_once)
            raw_content = response.choices[0].message.content or ""
            prompt_text = "\n".join(str(m.get("content") or "") for m in chat_messages)
            tokens_used = self._llm.tokens_from_usage(response.usage, prompt_text, raw_content)
        except Exception as exc:
            if is_rate_limit_error(exc):
                metrics.inc("llm_rate_limited")
                logger.error(
                    "Rate limit LLM wyczerpany dla sesji %s: %s", conversation_id, exc
                )
                final_result = rate_limit_fallback(message_id, conversation.config.language)
            else:
                metrics.inc("llm_errors")
                logger.error("Błąd wywołania API LLM dla sesji %s: %s", conversation_id, exc)
                final_result = llm_error_fallback(message_id, conversation.config.language)
            # Keep history parity with success path (user already appended in prepare).
            conversation.messages.append(
                {
                    "role": "assistant",
                    "content": final_result["answer"],
                    "message_id": message_id,
                    "penalty_applied": False,
                    "prompt_score": final_result.get("prompt_score"),
                    "sources": [],
                    "suggested_next_step": None,
                    "goal_progress": [],
                    "next_checkpoint": None,
                    "model": None,
                }
            )
            conversation.prompt_scores.append(int(final_result.get("prompt_score") or 5))
            conversation.touch()
            return self._persist_and_track(
                conversation_id,
                conversation,
                request.client_message_id,
                final_result,
                should_cache=False,
            )

        # 6. Post-processing odpowiedzi
        final_result = process_model_response(
            raw_content,
            conversation,
            message_id=message_id,
            tokens_used=tokens_used,
            code_changed=code_changed,
            sources=sources,
            model=used_model,
        )

        return self._persist_and_track(
            conversation_id, conversation, request.client_message_id, final_result, should_cache=True, request=request
        )

    async def reveal_hint(self, conversation_id: str, payload: RevealHintRequest) -> dict[str, Any]:
        """Udostępnia mocniejszą podpowiedź po weryfikacji trudności zadania."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        self._sessions.ensure_prelab_passed(conversation)

        if not reveal_gate_open(conversation.prompt_scores, is_frustrated_now=conversation.is_frustrated):
            raise RevealNotAllowed(
                "Reveal available only after sustained low scores / frustration"
            )

        if conversation.reveal_count >= MAX_REVEALS_PER_SESSION:
            raise RevealNotAllowed(
                f"Reveal quota exhausted (max {MAX_REVEALS_PER_SESSION} per session)"
            )

        lang = conversation.config.language
        code = payload.code_context.current_code if payload.code_context else conversation.last_code
        focus = payload.focus or ""

        prompt = (
            "You are a Socratic mentor giving ONE stronger unlocking hint.\n"
            "Hard rules:\n"
            "- Still NO full solution code, no complete methods/classes, no copy-pasteable patches.\n"
            "- At most one conceptual nudge (what to check / which concept), never implementation.\n"
            "- Do not include fenced code blocks with executable bodies.\n"
            f"Language: {'English' if lang == 'en' else 'Polish'}.\n"
            f"Assignment: {conversation.problem}\n"
            f"Student code:\n{code}\n"
            f"Focus: {focus}\n"
            'Return JSON: {"hint": "...", "suggested_next_step": "..."}'
        )

        response = await self._llm.create_chat_completion(
            model=self._llm.model_for(conversation),
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=250,
        )

        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"hint": raw, "suggested_next_step": ""}

        hint = str(data.get("hint") or "").strip()
        # Bezpiecznik: jeśli LLM mimo zakazu podał kod, podmień na bezpieczną wskazówkę
        if contains_revealed_code(hint):
            hint = (
                "Zrób jeden mały krok: sprawdź adnotację klasy i mapowanie ścieżki HTTP."
                if lang == "pl"
                else "Take one small step: verify the class annotation and HTTP path mapping."
            )

        conversation.reveal_count += 1
        conversation.touch()
        message_id = str(uuid.uuid4())

        conversation.messages.append(
            {
                "role": "assistant",
                "content": hint,
                "message_id": message_id,
                "penalty_applied": False,
                "prompt_score": None,
                "reveal": True,
            }
        )
        self._sessions.save_conversation(conversation_id, conversation)

        return {
            "message_id": message_id,
            "hint": hint,
            "suggested_next_step": data.get("suggested_next_step"),
            "reveal_count": conversation.reveal_count,
            "reveals_remaining": MAX_REVEALS_PER_SESSION - conversation.reveal_count,
        }

    def maybe_pedagogy_gate(
        self,
        conversation: Conversation,
        request: MessageRequest,
        *,
        message_id: str,
        code_changed: bool,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Krótki tor bez LLM: odmowa code-dump albo recall zapamiętanych identyfikatorów."""
        lang = conversation.config.language
        if is_code_dump_request(request.question):
            return finalize_gate_response(
                conversation,
                code_dump_refusal_payload(lang),
                message_id=message_id,
                code_changed=code_changed,
                sources=sources,
            )
        if is_recall_intent(request.question, conversation.pinned_identifiers):
            return finalize_gate_response(
                conversation,
                pinned_recall_payload(lang, conversation.pinned_identifiers),
                message_id=message_id,
                code_changed=code_changed,
                sources=sources,
            )
        return None

    def try_cache(
        self,
        conversation: Conversation,
        conversation_id: str,
        request: MessageRequest,
        message_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Odtwarza odpowiedź z cache (pomijane przy frustracji); aktualizuje historię sesji."""
        if conversation.is_frustrated:
            return None

        cached = self._cache.get_cached_response(
            conversation_id,
            request.question,
            request.code_context.error_logs,
            request.code_context.current_code,
        )
        if not cached:
            metrics.inc("cache_misses")
            return None

        metrics.inc("cache_hits")
        result = dict(cached)
        result["is_cached"] = True
        if message_id:
            result["message_id"] = message_id

        lang = conversation.config.language
        q_label = "Student question" if lang == "en" else "Pytanie studenta"
        conversation.messages.append({"role": "user", "content": f"{q_label}: {request.question}"})
        conversation.remember_identifiers(collect_identifier_tokens(request.question))
        conversation.last_code = request.code_context.current_code
        conversation.prompt_scores.append(result["prompt_score"])
        conversation.tokens_used_total += int(result.get("tokens_used") or 0)
        conversation.touch()

        conversation.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "message_id": result["message_id"],
                "penalty_applied": result.get("penalty_applied", False),
                "prompt_score": result.get("prompt_score"),
                "sources": result.get("sources") or [],
                "suggested_next_step": result.get("suggested_next_step"),
                "goal_progress": result.get("goal_progress") or [],
                "next_checkpoint": result.get("next_checkpoint"),
                "model": result.get("model"),
            }
        )

        debug = dict(result.get("debug_info") or {})
        debug["is_frustrated"] = conversation.is_frustrated
        result["debug_info"] = debug
        self.attach_checkpoint_coaching(conversation, result)
        return result

    def save_cache(
        self, conversation_id: str, request: MessageRequest, final_result: dict[str, Any]
    ) -> None:
        """Zapisuje finalną odpowiedź pod kluczem exact-match cache."""
        self._cache.save_to_cache(
            conversation_id,
            request.question,
            request.code_context.error_logs,
            request.code_context.current_code,
            final_result,
        )

    def track_result_metrics(self, result: dict[str, Any]) -> None:
        """Inkrementuje liczniki wiadomości, tokenów i kar."""
        metrics.inc("messages_total")
        metrics.inc("tokens_total", int(result.get("tokens_used") or 0))
        if result.get("penalty_applied"):
            metrics.inc("penalties_total")

    def remember_goal_progress(self, conversation: Conversation, result: dict[str, Any]) -> None:
        """Utrwala goal_progress z odpowiedzi LLM i odblokowuje powiązane checkpointy."""
        if progress := result.get("goal_progress"):
            conversation.goal_progress = list(progress)
            done = {g.get("goal") for g in progress if g.get("status") == "done"}
            for cp in conversation.config.checkpoints:
                if cp.after_goal in done and cp.id not in conversation.unlocked_checkpoints:
                    conversation.unlocked_checkpoints.append(cp.id)

    def attach_checkpoint_coaching(self, conversation: Conversation, result: dict[str, Any]) -> None:
        """Dobiera next_checkpoint i ewentualnie uzupełnia suggested_next_step."""
        conversation.ensure_goal_progress_defaults()
        done_goals = {g.get("goal") for g in conversation.goal_progress if g.get("status") == "done"}

        for cp in conversation.config.checkpoints:
            unlocked = cp.id in conversation.unlocked_checkpoints or (
                cp.after_goal is None or cp.after_goal in done_goals
            )
            if unlocked and cp.id not in conversation.unlocked_checkpoints:
                conversation.unlocked_checkpoints.append(cp.id)

        # Ostatni odblokowany checkpoint z hintem staje się „następnym” coachingiem.
        next_cp = None
        for cp in conversation.config.checkpoints:
            if cp.id not in conversation.unlocked_checkpoints:
                continue
            candidate = {"id": cp.id, "hint": cp.hint, "after_goal": cp.after_goal}
            if cp.after_goal is None or cp.after_goal in done_goals:
                next_cp = candidate

        result["next_checkpoint"] = next_cp
        if next_cp and next_cp.get("hint") and not result.get("suggested_next_step"):
            result["suggested_next_step"] = next_cp["hint"]

        for m in reversed(conversation.messages):
            if m.get("role") == "assistant" and m.get("message_id") == result.get("message_id"):
                m["next_checkpoint"] = next_cp
                if next_cp and next_cp.get("hint") and not m.get("suggested_next_step"):
                    m["suggested_next_step"] = next_cp["hint"]
                break

    def llm_generation_kwargs(self, conversation: Conversation) -> dict[str, Any]:
        """Parametry generacji (temperature/max_tokens) zależne od trybu agent_behavior.mode."""
        mode = getattr(conversation.config.agent_behavior, "mode", "debug") or "debug"
        params = generation_params(mode)
        return {
            "temperature": params["temperature"],
            "presence_penalty": 0.6,
            "frequency_penalty": 0.4,
            "max_tokens": params["max_tokens"],
            "response_format": {"type": "json_object"},
        }