import json
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple, Iterator

from app.application.response_pipeline import ResponsePipeline
from app.domain.conversation import Conversation, ChatMessage, MessageFeedback, GoalStatus
from app.domain.ports import ConversationRepository, LlmPort, LlmResult
from app.domain.exceptions import UnknownMessage, TokenBudgetExceeded
from app.application.session_service import SessionService
from app.application.prompts import build_system_prompt, build_user_prompt
from app.application.dto import (
    MessageRequest,
    MessageResponse,
    GoalProgressEntryDTO,
    NextCheckpointDTO,
    FeedbackRequest,
    FeedbackResponse,
)

STATUS_RANK: Dict[GoalStatus, int] = {
    "not_started": 0,
    "in_progress": 1,
    "done": 2,
}

class ChatService:
    def __init__(self, repo: ConversationRepository, session_svc: SessionService, llm: LlmPort, pipeline: Optional[ResponsePipeline] = None,):
        self.repo = repo
        self.session_svc = session_svc
        self.llm = llm
        self.pipeline = pipeline or ResponsePipeline()

    def list_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        conv = self.session_svc.get_or_404(conv_id)
        return [m.model_dump() for m in conv.messages]

    def _prepare_turn(self, conv_id: str, req: MessageRequest) -> Tuple[Conversation, Optional[MessageResponse], str, List[dict[str, str]]]:
        conv = self.session_svc.ensure_prelab_passed(conv_id)

        if req.client_message_id and req.client_message_id in conv.idempotency_cache:
            cached = MessageResponse(**conv.idempotency_cache[req.client_message_id])
            return conv, cached, "", []
        max_tokens = conv.config.max_tokens_per_session
        if max_tokens is not None and conv.token_usage >= max_tokens:
            raise TokenBudgetExceeded(
                language=conv.config.language,
                limit=max_tokens,
                used=conv.token_usage,
            )

        system_prompt = build_system_prompt(conv.config, conv.goal_progress)
        history_messages = [
            {"role": m.role, "content": m.content} for m in conv.messages[-10:]
        ]
        user_prompt_content = build_user_prompt(req.question, req.code_context)
        history_messages.append({"role": "user", "content": user_prompt_content})

        return conv, None, system_prompt, history_messages

    def _finalize_response(
            self,
            conv: Conversation,
            req: MessageRequest,
            system_prompt: str,
            history_messages: List[Dict[str, str]],
            llm_result: LlmResult,
    ) -> MessageResponse:
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
        next_cp = self.pipeline.evaluate_checkpoints(conv)
        lab_score = conv.calculate_lab_score()

        answer_text = str(parsed.get("answer", "Przeanalizujmy ten krok jeszcze raz."))
        prompt_feedback = str(parsed.get("prompt_feedback", "OK"))
        suggested_next_step = str(
            parsed.get("suggested_next_step", "Kontynuuj pracę nad kolejnym celem.")
        )

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

        prompt_score = 10 if (conv.all_goals_done() and not penalty_applied) else adjusted_score

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

        debug_info = dict(llm_result.debug_info or {})
        debug_info["fallback_json"] = is_fallback
        debug_info["language_drift_retried"] = drift_retried

        response_obj = MessageResponse(
            message_id=assistant_msg_id,
            answer=answer_text,
            prompt_score=prompt_score,
            prompt_feedback=prompt_feedback,
            tokens_used=total_tokens,
            penalty_applied=penalty_applied,
            sources=[],
            suggested_next_step=suggested_next_step,
            goal_progress=goal_progress_list,
            lab_score=lab_score,
            next_checkpoint=next_cp,
            model=used_model,
            debug_info=debug_info,
        )

        if req.client_message_id:
            conv.idempotency_cache[req.client_message_id] = response_obj.model_dump()

        self.repo.save(conv)
        return response_obj

    def send_message(self, conv_id: str, req: MessageRequest) -> MessageResponse:
        conv, cached, system_prompt, history_messages = self._prepare_turn(conv_id, req)
        if cached is not None:
            return cached

        llm_result = self.llm.generate_json(
            system_prompt=system_prompt, messages=history_messages
        )
        return self._finalize_response(conv, req, system_prompt, history_messages, llm_result)

    def stream_message(self, conv_id: str, req: MessageRequest) -> Iterator[str]:
        conv, cached, system_prompt, history_messages = self._prepare_turn(conv_id, req)

        def _ndjson_generator() -> Iterator[str]:
            if cached is not None:
                final_payload = {"type": "final", **cached.model_dump()}
                yield json.dump(final_payload, ensure_ascii=False) + "\n"
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
                model=getattr(self.llm, "model", "stream-model"),
            )
            final_response = self._finalize_response(conv, req, system_prompt, history_messages, llm_result)
            final_payload = {"type": "final", **final_response.model_dump()}
            yield json.dumps(final_payload, ensure_ascii=False) + "\n"
        return _ndjson_generator()

    def add_feedback(self, conv_id: str, message_id: str, req: FeedbackRequest) -> FeedbackResponse:
        conv = self.session_svc.get_or_404(conv_id)
        for msg in conv.messages:
            if msg.message_id == message_id:
                msg.feedback = MessageFeedback(rating=req.rating, comment=req.comment)
                self.repo.save(conv)
                return FeedbackResponse(status="recorded", message_id=message_id, rating=req.rating)
        raise UnknownMessage(f"Message {message_id} not found")