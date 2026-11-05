import json
import re
import time
import uuid
from typing import Dict, List, Optional, Any, Iterator, Tuple
from app.domain.conversation import Conversation, ChatMessage, MessageFeedback
from app.domain.ports import (
    ConversationRepository,
    LlmPort,
    LlmResult,
    RagPort,
    CachePort, WebhookPort,
)
from app.domain.exceptions import UnknownMessage, TokenBudgetExceeded, HintRevealForbidden
from app.application.session_service import SessionService
from app.application.prompts import build_system_prompt, build_user_prompt
from app.application.response_pipeline import ResponsePipeline, GIVEAWAY_REQUEST_RE
from app.application.security import SecurityGuard
from app.application.pedagogy_gates import PedagogyGates
# OLD: from app.infrastructure.cache_memory import build_cache_key  # hexagonal leak
from app.application.cache_keys import build_cache_key
from app.core.config import settings
from app.application.dto import (
    MessageRequest,
    MessageResponse,
    GoalProgressEntryDTO,
    FeedbackRequest,
    FeedbackResponse,
    HintRevealResponse,
)
from app.application.metrics import metrics
from app.application.grade_payload import build_grade_sync_payload

_CONCEPT_Q_RE = re.compile(
    r"(?i)\b(?:what\s+is|what's|czym\s+jest|co\s+to\s+(?:jest|znaczy)|co\s+oznacza|explain)\s+[`'\"]?(@?[A-Za-z_][\w.]*)"
)


class ChatService:
    def __init__(
        self,
        repo: ConversationRepository,
        session_svc: SessionService,
        llm: LlmPort,
        pipeline: Optional[ResponsePipeline] = None,
        security_guard: Optional[SecurityGuard] = None,
        pedagogy_gates: Optional[PedagogyGates] = None,
        rag: Optional[RagPort] = None,
        cache: Optional[CachePort] = None,
        webhooks: Optional[WebhookPort] = None,
    ):
        self.repo = repo
        self.session_svc = session_svc
        self.llm = llm
        self.pipeline = pipeline or ResponsePipeline()
        self.security_guard = security_guard or SecurityGuard(llm=llm)
        self.pedagogy_gates = pedagogy_gates or PedagogyGates()
        self.rag = rag
        self.cache = cache
        self.webhooks = webhooks

    def list_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        conv = self.session_svc.get_or_404(conv_id)
        return [m.model_dump() for m in conv.messages]

    def _emit_message_webhook(self, conv: Conversation, response_obj: MessageResponse) -> None:
        if self.webhooks is not None:
            self.webhooks.send_event(
                "message",
                {
                    "conversation_id": conv.id,
                    "message_id": response_obj.message_id,
                    "prompt_score": response_obj.prompt_score,
                    "lab_score": response_obj.lab_score,
                    "penalty_applied": response_obj.penalty_applied,
                    "tokens_used": response_obj.tokens_used,
                    "model": response_obj.model,
                },
            )

    def _build_gate_response(
        self,
        conv: Conversation,
        req: MessageRequest,
        gate_message_id: str,
        answer: str,
        feedback: str,
        next_step: str,
        penalty: bool,
        debug_info: Dict[str, Any],
    ) -> MessageResponse:
        user_msg = ChatMessage(
            message_id=str(uuid.uuid4()),
            role="user",
            content=req.question,
            client_message_id=req.client_message_id,
            code_context=req.code_context.model_dump(by_alias=True) if req.code_context else None,
        )
        assistant_msg = ChatMessage(
            message_id=gate_message_id,
            role="assistant",
            content=answer,
            prompt_score=1,
            prompt_feedback=feedback,
            penalty_applied=penalty,
            suggested_next_step=next_step,
            tokens_used=0,
            model="gate",
        )
        conv.messages.append(user_msg)
        conv.messages.append(assistant_msg)

        goal_progress_list = [
            GoalProgressEntryDTO(goal=g.id, status=conv.goal_progress.get(g.id, "not_started"))
            for g in conv.config.learning_context.goals
        ]
        next_cp = self.pipeline.evaluate_checkpoints(conv)

        response_obj = MessageResponse(
            message_id=gate_message_id,
            answer=answer,
            prompt_score=1,
            prompt_feedback=feedback,
            tokens_used=0,
            penalty_applied=penalty,
            sources=[],
            suggested_next_step=next_step,
            goal_progress=goal_progress_list,
            lab_score=conv.calculate_lab_score(),
            next_checkpoint=next_cp,
            model="gate",
            debug_info=debug_info,
        )

        if req.client_message_id:
            conv.idempotency_cache[req.client_message_id] = response_obj.model_dump()

        self.repo.save(conv)
        self._emit_message_webhook(conv, response_obj)
        return response_obj

    def _prepare_turn(
        self, conv_id: str, req: MessageRequest
    ) -> Tuple[Conversation, Optional[MessageResponse], str, List[Dict[str, str]], List[str]]:
        conv = self.session_svc.ensure_prelab_passed(conv_id)

        if req.client_message_id and req.client_message_id in conv.idempotency_cache:
            cached = MessageResponse(**conv.idempotency_cache[req.client_message_id])
            return conv, cached, "", [], []

        max_tokens = conv.config.max_tokens_per_session
        if max_tokens is not None and conv.token_usage >= max_tokens:
            raise TokenBudgetExceeded(
                language=conv.config.language,
                limit=max_tokens,
                used=conv.token_usage,
            )

        lang = conv.config.language
        code_ctx = req.code_context.to_domain() if req.code_context else None

        sec_verdict = self.security_guard.check(req.question, language=lang)
        if sec_verdict.blocked:
            blocked_resp = self._build_gate_response(
                conv=conv,
                req=req,
                gate_message_id="blocked",
                answer=(
                    "Wiadomość została zablokowana przez filtr bezpieczeństwa systemu. Skupmy się na merytorycznym rozwiązaniu zadania laboratoryjnego."
                    if lang == "pl"
                    else "Your message was blocked by the security filter. Let's focus on solving the lab assignment."
                ),
                feedback=sec_verdict.reason or "Security violation",
                next_step=(
                    "Zadaj pytanie dotyczące kodu lub problemu z laboratorium."
                    if lang == "pl"
                    else "Ask a question related to your lab code or problem."
                ),
                penalty=True,
                debug_info={"security_blocked": True, "stage": sec_verdict.stage, "reason": sec_verdict.reason},
            )
            return conv, blocked_resp, "", [], []

        ped_verdict = self.pedagogy_gates.evaluate(conv.config, req.question, code_ctx)
        if ped_verdict.rejected:
            # OLD: conv.frustration_streak += 1
            # Focus mode: still punish giveaways; soften other pedagogy rejects.
            if ped_verdict.reason_code == "giveaway_request" or not conv.in_focus_mode():
                conv.frustration_streak += 1
            rejected_resp = self._build_gate_response(
                conv=conv,
                req=req,
                gate_message_id="rejected",
                answer=ped_verdict.answer or (
                    "Zapytanie odrzucone przez bramkę dydaktyczną."
                    if lang == "pl"
                    else "Request rejected by the pedagogy gate."
                ),
                feedback=ped_verdict.prompt_feedback or (
                    "Odrzucono przez bramkę dydaktyczną."
                    if lang == "pl"
                    else "Rejected by pedagogy gate."
                ),
                next_step=ped_verdict.suggested_next_step or (
                    "Popraw zapytanie."
                    if lang == "pl"
                    else "Please revise your question."
                ),
                penalty=ped_verdict.penalty_applied,
                debug_info={
                    "pedagogy_rejected": True,
                    "reason_code": ped_verdict.reason_code,
                    "frustration_streak": conv.frustration_streak,
                },
            )
            return conv, rejected_resp, "", [], []

        rag_chunks = []
        rag_sources: List[str] = []
        if self.rag is not None and conv.config.reference_materials:
            rag_chunks = self.rag.retrieve(conv.id, req.question, top_k=settings.RAG_TOP_K)
            for chunk in rag_chunks:
                source_entry = f"{chunk.title} ({chunk.link})" if chunk.link else chunk.title
                if source_entry not in rag_sources:
                    rag_sources.append(source_entry)

        # Feature 2: error-aware tutoring — force debug mode when logs/diagnostics present.
        # OLD: system_prompt = build_system_prompt(conv.config, conv.goal_progress, rag_chunks=rag_chunks)
        mode_override = None
        if (
            getattr(conv.config, "auto_debug_on_errors", True)
            and code_ctx
            and (code_ctx.error_logs or code_ctx.diagnostics)
        ):
            mode_override = "debug"
        system_prompt = build_system_prompt(
            conv.config,
            conv.goal_progress,
            rag_chunks=rag_chunks,
            mode_override=mode_override,
        )
        history_messages = [
            {"role": m.role, "content": m.content}
            for m in conv.messages[-10:]
        ]
        user_prompt_content = build_user_prompt(req.question, code_ctx)
        history_messages.append({"role": "user", "content": user_prompt_content})

        return conv, None, system_prompt, history_messages, rag_sources

    def _finalize_response(
        self,
        conv: Conversation,
        req: MessageRequest,
        system_prompt: str,
        history_messages: List[Dict[str, str]],
        llm_result: LlmResult,
        sources: Optional[List[str]] = None,
    ) -> MessageResponse:
        prev_done_count = sum(1 for s in conv.goal_progress.values() if s == "done")

        parsed, is_fallback = self.pipeline.extract_json(llm_result.raw_content)
        total_tokens = llm_result.tokens_used
        used_model = llm_result.model
        drift_retried = False

        if parsed is None:
            parsed = self.pipeline.build_fallback_payload(llm_result.raw_content, conv)
        else:
            answer_candidate = str(parsed.get("answer", ""))
            if self.pipeline.has_language_drift(answer_candidate, conv.config.language):
                drift_retried = True
                lang_instruction = (
                    "UWAGA: Odpowiedziałeś w złym języku. Przetłumacz i zwróć identyczny JSON WYŁĄCZNIE PO POLSKU."
                    if conv.config.language == "pl"
                    else "WARNING: You answered in the wrong language. Return the exact same JSON structure STRICTLY IN ENGLISH."
                )
                retry_messages = history_messages + [
                    {"role": "assistant", "content": llm_result.raw_content},
                    {"role": "user", "content": lang_instruction},
                ]
                retry_res = self.llm.generate_json(
                    system_prompt=system_prompt, messages=retry_messages
                )
                total_tokens += retry_res.tokens_used
                used_model = retry_res.model
                retry_parsed, retry_fallback = self.pipeline.extract_json(retry_res.raw_content)
                if retry_parsed is not None and not retry_fallback:
                    parsed = retry_parsed
                    is_fallback = False

        goal_progress_list = self.pipeline.normalize_goals(conv, parsed.get("goal_progress", []))
        new_done_count = sum(1 for s in conv.goal_progress.values() if s == "done")
        next_cp = self.pipeline.evaluate_checkpoints(conv)
        lab_score = conv.calculate_lab_score()

        default_answer = (
            "Przeanalizujmy ten krok jeszcze raz."
            if conv.config.language == "pl"
            else "Let's review this step once more."
        )
        default_next = (
            "Kontynuuj pracę nad kolejnym celem."
            if conv.config.language == "pl"
            else "Continue working on the next goal."
        )
        answer_text = str(parsed.get("answer", default_answer))
        prompt_feedback = str(parsed.get("prompt_feedback", "OK"))
        suggested_next_step = str(parsed.get("suggested_next_step", default_next))

        try:
            raw_score = int(parsed.get("prompt_score", 5))
        except (TypeError, ValueError):
            raw_score = 5

        raw_penalty = bool(parsed.get("penalty_applied", False))
        adjusted_score, penalty_applied = self.pipeline.apply_code_penalty(
            answer=answer_text,
            question=req.question,
            prompt_score=raw_score,
            penalty_applied=raw_penalty,
        )

        # Feature 6: focus mode softens non-giveaway penalties.
        giveaway_q = bool(GIVEAWAY_REQUEST_RE.search(req.question or ""))
        if conv.in_focus_mode() and penalty_applied and not giveaway_q:
            # OLD: keep penalty_applied as computed
            penalty_applied = False

        prompt_score = 10 if (conv.all_goals_done() and not penalty_applied) else adjusted_score

        code_ctx_final = req.code_context.to_domain() if req.code_context else None
        has_errors = bool(
            code_ctx_final and (code_ctx_final.error_logs or code_ctx_final.diagnostics)
        )
        tutoring_mode = (
            "debug"
            if (
                getattr(conv.config, "auto_debug_on_errors", True)
                and has_errors
            )
            else conv.config.agent_behavior.mode
        )

        # Feature 3: checkpoint celebration + reflective nudge when goals advance.
        checkpoint_celebration = None
        if new_done_count > prev_done_count:
            conv.frustration_streak = 0
            if conv.config.language == "pl":
                checkpoint_celebration = (
                    "Świetnie — widać postęp w celach laboratorium. "
                    "Zanim pójdziesz dalej: jednym zdaniem powiedz, *dlaczego* ta zmiana działa."
                )
            else:
                checkpoint_celebration = (
                    "Nice progress on the lab goals. "
                    "Before you continue: in one sentence, explain *why* that change works."
                )
            answer_text = f"{checkpoint_celebration}\n\n{answer_text}"
            if next_cp and next_cp.unlocked and next_cp.hint:
                # Reflect then point at newly unlocked checkpoint hint (conceptual, not full solution).
                suggested_next_step = next_cp.hint
        # OLD: elif penalty_applied or prompt_score <= 4 or has_errors:
        #          conv.frustration_streak += 1
        elif conv.in_focus_mode() and not giveaway_q:
            pass  # soft window: do not grow frustration for low scores / errors
        elif penalty_applied or prompt_score <= 4 or has_errors:
            conv.frustration_streak += 1

        # Feature 4: concept glossary card from RAG when question looks definitional.
        concept_card = None
        m = _CONCEPT_Q_RE.search(req.question or "")
        if m and sources:
            term = m.group(1)
            concept_card = {
                "term": term,
                "sources": sources[:3],
                "note": (
                    "Wyjaśnienie oparte na materiałach laboratorium (RAG)."
                    if conv.config.language == "pl"
                    else "Explanation grounded in lab reference materials (RAG)."
                ),
            }

        user_msg = ChatMessage(
            message_id=str(uuid.uuid4()),
            role="user",
            content=req.question,
            client_message_id=req.client_message_id,
            code_context=req.code_context.model_dump(by_alias=True) if req.code_context else None,
        )
        assistant_msg_id = str(uuid.uuid4())
        assistant_msg = ChatMessage(
            message_id=assistant_msg_id,
            role="assistant",
            content=answer_text,
            prompt_score=prompt_score,
            prompt_feedback=prompt_feedback,
            penalty_applied=penalty_applied,
            suggested_next_step=suggested_next_step,
            tokens_used=total_tokens,
            model=used_model,
        )

        conv.messages.append(user_msg)
        conv.messages.append(assistant_msg)
        conv.token_usage += total_tokens

        if conv.all_goals_done() and conv.grade_payload is None:
            grade = build_grade_sync_payload(conv, trigger="all_goals_done")
            conv.grade_payload = grade
            if self.webhooks is not None:
                self.webhooks.send_event("grade_sync_prepared", grade)

        debug_info = dict(llm_result.debug_info or {})
        debug_info["fallback_json"] = is_fallback
        debug_info["language_drift_retried"] = drift_retried
        debug_info["frustration_streak"] = conv.frustration_streak
        debug_info["tutoring_mode"] = tutoring_mode
        debug_info["in_focus_mode"] = conv.in_focus_mode()
        debug_info.setdefault("cache_hit", False)

        response_obj = MessageResponse(
            message_id=assistant_msg_id,
            answer=answer_text,
            prompt_score=prompt_score,
            prompt_feedback=prompt_feedback,
            tokens_used=total_tokens,
            penalty_applied=penalty_applied,
            sources=sources or [],
            suggested_next_step=suggested_next_step,
            goal_progress=goal_progress_list,
            lab_score=lab_score,
            next_checkpoint=next_cp,
            model=used_model,
            debug_info=debug_info,
            tutoring_mode=tutoring_mode,
            checkpoint_celebration=checkpoint_celebration,
            concept_card=concept_card,
            in_focus_mode=conv.in_focus_mode(),
        )

        if req.client_message_id:
            conv.idempotency_cache[req.client_message_id] = response_obj.model_dump()

        self.repo.save(conv)
        self._emit_message_webhook(conv, response_obj)
        return response_obj

    def send_message(self, conv_id: str, req: MessageRequest) -> MessageResponse:
        metrics.inc_messages()
        conv, early_response, system_prompt, history_messages, rag_sources = self._prepare_turn(
            conv_id, req
        )
        if early_response is not None:
            return early_response

        model_name = getattr(self.llm, "model", "default")
        cache_key = build_cache_key(system_prompt, history_messages, model=model_name)
        llm_result = self.cache.get(cache_key) if self.cache is not None else None

        if llm_result is None:
            llm_result = self.llm.generate_json(
                system_prompt=system_prompt, messages=history_messages
            )
            if self.cache is not None:
                self.cache.set(cache_key, llm_result)

        return self._finalize_response(
            conv, req, system_prompt, history_messages, llm_result, sources=rag_sources
        )

    def stream_message(self, conv_id: str, req: MessageRequest) -> Iterator[str]:
        metrics.inc_messages()
        conv, early_response, system_prompt, history_messages, rag_sources = self._prepare_turn(
            conv_id, req
        )

        def _ndjson_generator() -> Iterator[str]:
            if early_response is not None:
                final_payload = {"type": "final", **early_response.model_dump()}
                yield json.dumps(final_payload, ensure_ascii=False) + "\n"
                return

            model_name = getattr(self.llm, "model", "stream-model")
            cache_key = build_cache_key(system_prompt, history_messages, model=model_name)
            cached_llm = self.cache.get(cache_key) if self.cache is not None else None

            if cached_llm is not None:
                token_event = {"type": "token", "text": cached_llm.raw_content}
                yield json.dumps(token_event, ensure_ascii=False) + "\n"
                final_response = self._finalize_response(
                    conv, req, system_prompt, history_messages, cached_llm, sources=rag_sources
                )
                final_payload = {"type": "final", **final_response.model_dump()}
                yield json.dumps(final_payload, ensure_ascii=False) + "\n"
                return

            collected_chunks: List[str] = []
            for chunk_text in self.llm.stream_json(
                system_prompt=system_prompt, messages=history_messages
            ):
                if chunk_text:
                    collected_chunks.append(chunk_text)
                    token_event = {"type": "token", "text": chunk_text}
                    yield json.dumps(token_event, ensure_ascii=False) + "\n"

            full_raw = "".join(collected_chunks)
            estimated_tokens = max(1, len(full_raw) // 4)
            llm_result = LlmResult(
                raw_content=full_raw,
                tokens_used=estimated_tokens,
                model=model_name,
            )
            if self.cache is not None:
                self.cache.set(cache_key, llm_result)

            final_response = self._finalize_response(
                conv, req, system_prompt, history_messages, llm_result, sources=rag_sources
            )
            final_payload = {"type": "final", **final_response.model_dump()}
            yield json.dumps(final_payload, ensure_ascii=False) + "\n"

        return _ndjson_generator()

    def reveal_hint(self, conv_id: str) -> HintRevealResponse:
        conv = self.session_svc.ensure_prelab_passed(conv_id)
        max_hints = conv.config.max_hints
        required_streak = conv.config.frustration_threshold

        if conv.hints_revealed >= max_hints:
            raise HintRevealForbidden(
                reason="quota_exceeded",
                language=conv.config.language,
                streak=conv.frustration_streak,
                required_streak=required_streak,
                hints_used=conv.hints_revealed,
                max_hints=max_hints,
            )

        if conv.frustration_streak < required_streak:
            raise HintRevealForbidden(
                reason="insufficient_streak",
                language=conv.config.language,
                streak=conv.frustration_streak,
                required_streak=required_streak,
                hints_used=conv.hints_revealed,
                max_hints=max_hints,
            )

        # OLD: available_hints = list(conv.config.hints)
        # Feature 9: prefer hint_ladder when present.
        available_hints = conv.config.resolved_hint_texts()
        available_levels = conv.config.resolved_hint_levels()
        for cp in conv.config.checkpoints:
            if cp.hint and cp.hint not in available_hints:
                available_hints.append(cp.hint)
                available_levels.append("concept")

        idx = conv.hints_revealed
        hint_level = available_levels[idx] if idx < len(available_levels) else "nudge"
        if idx < len(available_hints):
            hint_text = available_hints[idx]
        else:
            pending_goals = [
                g.description
                for g in conv.config.learning_context.goals
                if conv.goal_progress.get(g.id) != "done"
            ]
            target_desc = pending_goals[0] if pending_goals else conv.config.evaluation_criteria
            hint_text = (
                f"Wskazówka #{idx + 1}: Skup się na kroku: {target_desc}."
                if conv.config.language == "pl"
                else f"Hint #{idx + 1}: Focus on completing: {target_desc}."
            )

        conv.hints_revealed += 1
        conv.revealed_hints.append(hint_text)
        conv.highest_hint_level = hint_level
        conv.frustration_streak = 0
        self.repo.save(conv)

        return HintRevealResponse(
            hint=hint_text,
            hints_used=conv.hints_revealed,
            max_hints=max_hints,
            hints_remaining=max(0, max_hints - conv.hints_revealed),
            frustration_streak_reset=True,
            forced=False,
            hint_level=hint_level,
        )

    def force_reveal_hint(
        self,
        conv_id: str,
        reason: Optional[str] = None,
        custom_hint: Optional[str] = None,
        hint_level: Optional[str] = None,
    ) -> HintRevealResponse:
        """Professor override: reveal next hint without frustration streak check."""
        conv = self.session_svc.ensure_prelab_passed(conv_id)
        max_hints = conv.config.max_hints

        # Feature 11: custom intervention hint text from professor.
        if custom_hint and custom_hint.strip():
            text = custom_hint.strip()
            level = hint_level or "concept"
            conv.hints_revealed += 1
            conv.revealed_hints.append(text)
            conv.highest_hint_level = level
            conv.frustration_streak = 0
            conv.events.append(
                {
                    "type": "force_hint",
                    "meta": {
                        "reason": reason or "professor_override",
                        "custom": True,
                        "hint_level": level,
                    },
                    "timestamp": time.time(),
                }
            )
            self.repo.save(conv)
            return HintRevealResponse(
                hint=text,
                hints_used=conv.hints_revealed,
                max_hints=max_hints,
                hints_remaining=max(0, max_hints - conv.hints_revealed),
                frustration_streak_reset=True,
                forced=True,
                hint_level=level,
            )

        if conv.hints_revealed >= max_hints:
            raise HintRevealForbidden(
                reason="quota_exceeded",
                language=conv.config.language,
                streak=conv.frustration_streak,
                required_streak=conv.config.frustration_threshold,
                hints_used=conv.hints_revealed,
                max_hints=max_hints,
            )

        # Temporarily satisfy streak so reveal_hint path stays single source of truth
        conv.frustration_streak = max(conv.frustration_streak, conv.config.frustration_threshold)
        self.repo.save(conv)
        result = self.reveal_hint(conv_id)
        conv = self.session_svc.get_or_404(conv_id)
        conv.events.append(
            {
                "type": "force_hint",
                "meta": {
                    "reason": reason or "professor_override",
                    "hint_index": conv.hints_revealed,
                    "hint_level": result.hint_level,
                },
                "timestamp": time.time(),
            }
        )
        self.repo.save(conv)
        return HintRevealResponse(
            hint=result.hint,
            hints_used=result.hints_used,
            max_hints=result.max_hints,
            hints_remaining=result.hints_remaining,
            frustration_streak_reset=True,
            forced=True,
            hint_level=result.hint_level,
        )

    def add_feedback(self, conv_id: str, message_id: str, req: FeedbackRequest) -> FeedbackResponse:
        conv = self.session_svc.get_or_404(conv_id)
        for msg in conv.messages:
            if msg.message_id == message_id:
                msg.feedback = MessageFeedback(rating=req.rating, comment=req.comment)
                self.repo.save(conv)
                return FeedbackResponse(status="recorded", message_id=message_id, rating=req.rating)
        raise UnknownMessage(f"Message {message_id} not found")