"""Orkiestracja czatu dydaktycznego: RAG, bramki pedagogiczne, cache, wywołania LLM i reveal."""

from __future__ import annotations

import difflib
import json
import logging
from typing import Any
import uuid

from app.application.dto import MessageRequest, RevealHintRequest
from app.application.llm_errors import (
    call_with_rate_limit_policy,
    is_rate_limit_error,
    is_structured_output_unsupported,
)
from app.application.pedagogy_gates import (
    code_dump_refusal_payload,
    finalize_gate_response,
    is_code_dump_request,
    is_recall_intent,
    pinned_recall_payload,
)
from app.application.prompts import (
    build_system_prompt,
    format_code_context_block,
    generation_params,
)
from app.application.response_pipeline import (
    answer_has_language_drift,
    collect_identifier_tokens,
    compress_history,
    contains_revealed_code,
    format_pinned_identifiers_note,
    language_retry_note,
    llm_error_fallback,
    parse_model_json,
    process_model_response,
    rate_limit_fallback,
)
from app.application.sessions import SessionService
from app.core.config import MAX_REVEALS_PER_SESSION
from app.core.metrics import metrics
from app.domain.conversation import Conversation, reveal_gate_open
from app.domain.exceptions import RevealNotAllowed
from app.ports import CachePort, LlmPort, RagPort

logger = logging.getLogger(__name__)


class ChatService:
    """Główny orkiestrator konwersacji dydaktycznej integrujący wiedzę domenową, model LLM i guardraile."""

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

    @staticmethod
    def _compute_code_diff(old_code: str | None, new_code: str, language: str) -> tuple[str, bool]:
        """Wyznacza zunifikowany diff kodu użytkownika od czasu poprzedniej interakcji."""
        if not old_code or old_code == new_code:
            return "", False

        diff_lines = list(
            difflib.unified_diff(
                old_code.splitlines(),
                new_code.splitlines(),
                lineterm="",
            )
        )
        if not diff_lines:
            return "", False

        header = (
            "Changes made by student since last prompt:"
            if language == "en"
            else "Zmiany w kodzie wprowadzone przez studenta od ostatniej porady:"
        )
        formatted_diff = "\n".join(diff_lines)
        return f"\n{header}\n```diff\n{formatted_diff}\n```\n", True

    async def prepare_chat_context(
        self,
        conversation_id: str,
        conversation: Conversation,
        request: MessageRequest,
        *,
        append_user: bool = True,
    ) -> tuple[list[dict[str, Any]], bool, list[dict[str, Any]]]:
        """Przygotowuje pełen zestaw wiadomości dla API LLM wraz z kontekstem RAG i historią."""
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
        question_label = "Student question" if lang == "en" else "Pytanie studenta"

        user_content = (
            f"{context_block}\n"
            f"{code_diff_text}"
            f"{question_label}: {request.question}\n\n"
            f"{rag_context}"
        )

        if append_user:
            conversation.messages.append({"role": "user", "content": user_content})
            conversation.remember_identifiers(collect_identifier_tokens(request.question))

        history_clean = [
            {"role": m["role"], "content": m["content"]} for m in conversation.messages
        ]
        history_compressed = compress_history(
            history_clean,
            language=lang,
            pinned_identifiers=conversation.pinned_identifiers,
        )

        task_label = "Main assignment:" if lang == "en" else "Zadanie główne:"
        system_messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(conversation)},
            {"role": "system", "content": f"{task_label} {conversation.problem}"},
        ]

        if pinned_note := format_pinned_identifiers_note(conversation.pinned_identifiers, lang):
            system_messages.append({"role": "system", "content": pinned_note})

        return [*system_messages, *history_compressed], code_changed, sources

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
        """Utrwala stan sesji, obsługuje idempotencję, zapisuje cache i rejestruje metryki."""
        self.remember_goal_progress(conversation, result)
        self.attach_checkpoint_coaching(conversation, result)

        if should_cache and request:
            self.save_cache(conversation_id, request, result)

        stored = self._sessions.store_idempotent(conversation_id, client_message_id, result)
        self._sessions.save_conversation(conversation_id, conversation)
        self.track_result_metrics(stored)
        return stored

    def _record_fallback_turn(
        self,
        conversation: Conversation,
        fallback_result: dict[str, Any],
        message_id: str,
    ) -> None:
        """Uzupełnia historię konwersacji o awaryjną odpowiedź tekstową."""
        score = int(fallback_result.get("prompt_score") or 5)
        conversation.messages.append({
            "role": "assistant",
            "content": fallback_result["answer"],
            "message_id": message_id,
            "penalty_applied": False,
            "prompt_score": score,
            "sources": [],
            "suggested_next_step": None,
            "goal_progress": [],
            "next_checkpoint": None,
            "model": None,
        })
        conversation.prompt_scores.append(score)
        conversation.touch()

    async def _execute_llm_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        generation_kwargs: dict[str, Any],
    ) -> Any:
        """Wywołuje model z automatycznym ponowieniem bez structured outputs przy braku wsparcia."""
        try:
            return await self._llm.create_chat_completion(
                model=model,
                messages=messages,
                **generation_kwargs,
            )
        except Exception as exc:
            if not is_structured_output_unsupported(exc):
                raise
            logger.warning(
                "Model nie obsługuje structured outputs — ponawianie bez response_format (%s)",
                exc,
            )
            fallback_kwargs = {k: v for k, v in generation_kwargs.items() if k != "response_format"}
            return await self._llm.create_chat_completion(
                model=model,
                messages=messages,
                **fallback_kwargs,
            )

    async def send_message(self, conversation_id: str, request: MessageRequest) -> dict[str, Any]:
        """Główny potok obsługi zapytania: weryfikacja, idempotencja, cache, bramki i LLM."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        self._sessions.ensure_prelab_passed(conversation)
        self._sessions.ensure_token_budget(conversation)

        # 1. Sprawdzenie idempotencji klienta
        if prior := self._sessions.lookup_idempotent(conversation_id, request.client_message_id):
            self.track_result_metrics(prior)
            return prior

        # 2. Próba odzyskania odpowiedzi z cache (omijana przy wykrytej frustracji)
        if cached := self.try_cache(conversation, conversation_id, request):
            return self._persist_and_track(
                conversation_id, conversation, request.client_message_id, cached, should_cache=False
            )

        # 3. Złożenie promptu, historii oraz kontekstu RAG
        chat_messages, code_changed, sources = await self.prepare_chat_context(
            conversation_id, conversation, request
        )
        message_id = str(uuid.uuid4())

        # 4. Bramki dydaktyczne (odmowa podania gotowca lub przypomnienie zapamiętanych nazw)
        if gated := self.maybe_pedagogy_gate(
            conversation, request, message_id=message_id, code_changed=code_changed, sources=sources
        ):
            return self._persist_and_track(
                conversation_id,
                conversation,
                request.client_message_id,
                gated,
                should_cache=True,
                request=request,
            )

        # 5. Przygotowanie parametrów i wysłanie zapytania do LLM
        gen_kwargs = self.llm_generation_kwargs(conversation)
        model_name = self._llm.model_for(conversation)

        try:
            response, used_model = await call_with_rate_limit_policy(
                model_name,
                lambda m: self._execute_llm_completion(m, chat_messages, gen_kwargs),
            )
            raw_content = response.choices[0].message.content or ""
            prompt_text = "\n".join(str(m.get("content") or "") for m in chat_messages)
            tokens_used = self._llm.tokens_from_usage(response.usage, prompt_text, raw_content)

            # Jednorazowy retry przy driftcie języka (np. cyrylica w sesji PL)
            preview = parse_model_json(raw_content, conversation.config.language)
            preview_answer = str(preview.get("answer") or "")
            if answer_has_language_drift(preview_answer, conversation.config.language):
                metrics.inc("language_drift_retry")
                logger.warning(
                    "Drift języka w odpowiedzi LLM (sesja %s) — ponowienie z przypomnieniem",
                    conversation_id,
                )
                retry_messages = [
                    *chat_messages,
                    {"role": "user", "content": language_retry_note(conversation.config.language)},
                ]
                try:
                    response, used_model = await call_with_rate_limit_policy(
                        used_model or model_name,
                        lambda m: self._execute_llm_completion(m, retry_messages, gen_kwargs),
                    )
                    raw_content = response.choices[0].message.content or ""
                    prompt_text = "\n".join(
                        str(m.get("content") or "") for m in retry_messages
                    )
                    tokens_used += self._llm.tokens_from_usage(
                        response.usage, prompt_text, raw_content
                    )
                except Exception as retry_exc:
                    logger.warning(
                        "Retry driftu języka nieudany (sesja %s): %s — zostawiam pierwszą odpowiedź",
                        conversation_id,
                        retry_exc,
                    )
        except Exception as exc:
            if is_rate_limit_error(exc):
                metrics.inc("llm_rate_limited")
                logger.error("Rate limit LLM wyczerpany dla sesji %s: %s", conversation_id, exc)
                final_result = rate_limit_fallback(message_id, conversation.config.language)
            else:
                metrics.inc("llm_errors")
                logger.error("Błąd wywołania API LLM dla sesji %s: %s", conversation_id, exc)
                final_result = llm_error_fallback(
                    message_id, conversation.config.language, exc=exc
                )

            self._record_fallback_turn(conversation, final_result, message_id)
            return self._persist_and_track(
                conversation_id,
                conversation,
                request.client_message_id,
                final_result,
                should_cache=False,
            )

        # 6. Post-processing surowego JSON-a od modelu
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
            conversation_id,
            conversation,
            request.client_message_id,
            final_result,
            should_cache=True,
            request=request,
        )

    async def reveal_hint(self, conversation_id: str, payload: RevealHintRequest) -> dict[str, Any]:
        """Udostępnia mocniejszą podpowiedź po spełnieniu warunków frustracji i limitów sesji."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        self._sessions.ensure_prelab_passed(conversation)

        if not reveal_gate_open(conversation.prompt_scores, is_frustrated_now=conversation.is_frustrated):
            raise RevealNotAllowed("Reveal available only after sustained low scores / frustration")

        if conversation.reveal_count >= MAX_REVEALS_PER_SESSION:
            raise RevealNotAllowed(f"Reveal quota exhausted (max {MAX_REVEALS_PER_SESSION} per session)")

        lang = conversation.config.language
        code = payload.code_context.current_code if payload.code_context else conversation.last_code
        focus = payload.focus or ""

        reveal_prompt = (
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
            messages=[{"role": "system", "content": reveal_prompt}],
            response_format={"type": "json_object"},
            max_tokens=250,
        )

        raw_response = response.choices[0].message.content or "{}"
        try:
            parsed_data = json.loads(raw_response)
        except json.JSONDecodeError:
            parsed_data = {"hint": raw_response, "suggested_next_step": ""}

        hint = str(parsed_data.get("hint") or "").strip()

        # Bezpiecznik: podmiana na wskazówkę pojęciową, jeśli model mimo zakazu wygenerował kod
        if contains_revealed_code(hint):
            hint = (
                "Zrób jeden mały krok: sprawdź adnotację klasy i mapowanie ścieżki HTTP."
                if lang == "pl"
                else "Take one small step: verify the class annotation and HTTP path mapping."
            )

        conversation.reveal_count += 1
        conversation.touch()
        message_id = str(uuid.uuid4())

        conversation.messages.append({
            "role": "assistant",
            "content": hint,
            "message_id": message_id,
            "penalty_applied": False,
            "prompt_score": None,
            "reveal": True,
        })
        self._sessions.save_conversation(conversation_id, conversation)

        return {
            "message_id": message_id,
            "hint": hint,
            "suggested_next_step": parsed_data.get("suggested_next_step"),
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
        """Krótki tor deterministyczny: odmowa generowania gotowca lub przypomnienie nazwy."""
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
        """Odtwarza odpowiedź z pamięci podręcznej i aktualizuje stan sesji."""
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

        conversation.messages.append({
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
        })

        debug = dict(result.get("debug_info") or {})
        debug["is_frustrated"] = conversation.is_frustrated
        result["debug_info"] = debug

        self.attach_checkpoint_coaching(conversation, result)
        return result

    def save_cache(
        self,
        conversation_id: str,
        request: MessageRequest,
        final_result: dict[str, Any],
    ) -> None:
        """Zapisuje zweryfikowaną odpowiedź w pamięci podręcznej exact-match."""
        self._cache.save_to_cache(
            conversation_id,
            request.question,
            request.code_context.error_logs,
            request.code_context.current_code,
            final_result,
        )

    @staticmethod
    def track_result_metrics(result: dict[str, Any]) -> None:
        """Inkrementuje liczniki wykonanych zapytań, tokenów oraz nałożonych kar."""
        metrics.inc("messages_total")
        metrics.inc("tokens_total", int(result.get("tokens_used") or 0))
        if result.get("penalty_applied"):
            metrics.inc("penalties_total")

    @staticmethod
    def remember_goal_progress(conversation: Conversation, result: dict[str, Any]) -> None:
        """Zapisuje zaktualizowane cele dydaktyczne i odblokowuje checkpointy sesji."""
        if progress := result.get("goal_progress"):
            conversation.goal_progress = list(progress)
            done_goals = {g.get("goal") for g in progress if g.get("status") == "done"}
            for cp in conversation.config.checkpoints:
                if cp.after_goal in done_goals and cp.id not in conversation.unlocked_checkpoints:
                    conversation.unlocked_checkpoints.append(cp.id)

    def attach_checkpoint_coaching(
        self,
        conversation: Conversation,
        result: dict[str, Any],
    ) -> None:
        """Wyznacza aktywny checkpoint i synchronizuje go z odpowiedzią oraz historią wiadomości."""
        conversation.ensure_goal_progress_defaults()
        done_goals = {g.get("goal") for g in conversation.goal_progress if g.get("status") == "done"}

        # Odblokowanie checkpointów, które nie wymagają wcześniejszych celów
        for cp in conversation.config.checkpoints:
            can_unlock = (
                cp.id in conversation.unlocked_checkpoints
                or cp.after_goal is None
                or cp.after_goal in done_goals
            )
            if can_unlock and cp.id not in conversation.unlocked_checkpoints:
                conversation.unlocked_checkpoints.append(cp.id)

        # Dobór ostatniego odblokowanego punktu z podpowiedzią
        next_cp = None
        for cp in conversation.config.checkpoints:
            if cp.id not in conversation.unlocked_checkpoints:
                continue
            if cp.after_goal is None or cp.after_goal in done_goals:
                next_cp = {"id": cp.id, "hint": cp.hint, "after_goal": cp.after_goal}

        result["next_checkpoint"] = next_cp
        if next_cp and next_cp.get("hint") and not result.get("suggested_next_step"):
            result["suggested_next_step"] = next_cp["hint"]

        # Synchronizacja z ostatnim wpisem asystenta w historii sesji
        target_msg_id = result.get("message_id")
        for msg in reversed(conversation.messages):
            if msg.get("role") == "assistant" and msg.get("message_id") == target_msg_id:
                msg["next_checkpoint"] = next_cp
                if next_cp and next_cp.get("hint") and not msg.get("suggested_next_step"):
                    msg["suggested_next_step"] = next_cp["hint"]
                break

    @staticmethod
    def llm_generation_kwargs(conversation: Conversation) -> dict[str, Any]:
        """Konfiguruje parametry wnioskowania (temperatura, kary powtórzeń, limity tokenów)."""
        mode = getattr(conversation.config.agent_behavior, "mode", "debug") or "debug"
        params = generation_params(mode)
        return {
            "temperature": params["temperature"],
            "presence_penalty": 0.6,
            "frequency_penalty": 0.4,
            "max_tokens": params["max_tokens"],
            "response_format": {"type": "json_object"},
        }