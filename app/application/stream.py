"""Strumieniowanie odpowiedzi NDJSON (token + final) z tymi samymi bramkami co sync chat."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.application.chat import ChatService
from app.application.dto import MessageRequest
from app.application.response_pipeline import (
    IncrementalAnswerExtractor,
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
from app.core.metrics import metrics
from app.ports import LlmPort

STREAM_CHUNK_SIZE = 40
_STREAM_DONE = object()
logger = logging.getLogger(__name__)


class StreamService:
    """Serwis realizujący asynchroniczny streaming odpowiedzi dydaktycznych w formacie NDJSON."""

    def __init__(
        self,
        sessions: SessionService,
        chat: ChatService,
        llm: LlmPort,
    ) -> None:
        self._sessions = sessions
        self._chat = chat
        self._llm = llm

    async def _ndjson_stream_result(self, result: dict[str, Any]) -> AsyncIterator[str]:
        """Syntetyczne odtworzenie strumienia (dla cache, idempotencji i błędów)."""
        answer = str(result.get("answer") or "")
        for i in range(0, len(answer), STREAM_CHUNK_SIZE):
            piece = answer[i : i + STREAM_CHUNK_SIZE]
            yield json.dumps({"type": "token", "text": piece}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "final", **result}, ensure_ascii=False) + "\n"

    async def _call_llm_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        gen_params: dict[str, Any],
        *,
        use_response_format: bool = True,
    ) -> Any:
        """Wywołuje strumień LLM; opcjonalnie bez response_format (modele bez JSON mode)."""
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": gen_params["temperature"],
            "presence_penalty": gen_params["presence_penalty"],
            "frequency_penalty": gen_params["frequency_penalty"],
            "max_tokens": gen_params["max_tokens"],
            "stream": True,
        }
        if use_response_format and gen_params.get("response_format") is not None:
            kwargs["response_format"] = gen_params["response_format"]

        async def _create(call_kwargs: dict[str, Any]) -> Any:
            try:
                return await self._llm.create_chat_completion(
                    **call_kwargs, stream_options={"include_usage": True}
                )
            except TypeError:
                logger.debug("Dostawca LLM nie obsługuje stream_options, ponawianie bez tej opcji.")
                return await self._llm.create_chat_completion(**call_kwargs)

        return await _create(kwargs)

    async def stream_message(
        self, conversation_id: str, request: MessageRequest, message_id: str
    ) -> AsyncIterator[str]:
        """Główny generator strumieniowy NDJSON: emituje tokeny 'live', a na końcu obiekt 'final'."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        self._sessions.ensure_prelab_passed(conversation)
        self._sessions.ensure_token_budget(conversation)

        lang = conversation.config.language

        if prior := self._sessions.lookup_idempotent(conversation_id, request.client_message_id):
            self._chat.track_result_metrics(prior)
            async for line in self._ndjson_stream_result(prior):
                yield line
            return

        if cached := self._chat.try_cache(conversation, conversation_id, request, message_id):
            stored = self._sessions.store_idempotent(conversation_id, request.client_message_id, cached)
            self._sessions.save_conversation(conversation_id, conversation)
            self._chat.track_result_metrics(stored)
            async for line in self._ndjson_stream_result(stored):
                yield line
            return

        chat_messages, code_changed, sources = await self._chat.prepare_chat_context(
            conversation_id, conversation, request
        )

        if gated := self._chat.maybe_pedagogy_gate(
            conversation, request, message_id=message_id, code_changed=code_changed, sources=sources
        ):
            self._chat.remember_goal_progress(conversation, gated)
            self._chat.attach_checkpoint_coaching(conversation, gated)
            self._chat.save_cache(conversation_id, request, gated)
            stored = self._sessions.store_idempotent(conversation_id, request.client_message_id, gated)
            self._sessions.save_conversation(conversation_id, conversation)
            self._chat.track_result_metrics(stored)
            async for line in self._ndjson_stream_result(stored):
                yield line
            return

        gen = self._chat.llm_generation_kwargs(conversation)
        model_name = self._llm.model_for(conversation)
        extractor = IncrementalAnswerExtractor()
        full_raw_response = ""
        usage = None
        token_q: asyncio.Queue[Any] = asyncio.Queue()

        async def _consume_stream(model: str, *, use_response_format: bool) -> None:
            nonlocal full_raw_response, usage, extractor
            extractor = IncrementalAnswerExtractor()
            full_raw_response = ""
            usage = None
            stream_response = await self._call_llm_stream(
                model,
                chat_messages,
                gen,
                use_response_format=use_response_format,
            )
            async for chunk in stream_response:
                if chunk_usage := getattr(chunk, "usage", None):
                    usage = chunk_usage
                if not chunk.choices:
                    continue
                piece = chunk.choices[0].delta.content or ""
                if not piece:
                    continue
                full_raw_response += piece
                if delta := extractor.feed(piece):
                    await token_q.put(
                        json.dumps({"type": "token", "text": delta}, ensure_ascii=False) + "\n"
                    )

        async def _stream_once(model: str) -> None:
            try:
                await _consume_stream(model, use_response_format=True)
            except Exception as first_exc:
                if not is_structured_output_unsupported(first_exc):
                    raise
                logger.warning(
                    "Stream: structured outputs niedostępne — retry bez response_format (%s)",
                    first_exc,
                )
                await _consume_stream(model, use_response_format=False)

        async def _run_policy() -> tuple[Any, str]:
            try:
                return await call_with_rate_limit_policy(model_name, _stream_once)
            finally:
                await token_q.put(_STREAM_DONE)

        policy_task = asyncio.create_task(_run_policy())

        while True:
            item = await token_q.get()
            if item is _STREAM_DONE:
                break
            yield item

        try:
            _, used_model = await policy_task
        except Exception as exc:
            if is_rate_limit_error(exc):
                metrics.inc("llm_rate_limited")
                logger.error(
                    "Rate limit strumienia LLM wyczerpany dla sesji %s: %s",
                    conversation_id,
                    exc,
                )
                fallback = rate_limit_fallback(message_id, lang)
            else:
                metrics.inc("llm_errors")
                logger.error("Błąd strumieniowania LLM dla sesji %s: %s", conversation_id, exc)
                fallback = llm_error_fallback(message_id, lang, exc=exc)
            conversation.messages.append(
                {
                    "role": "assistant",
                    "content": fallback["answer"],
                    "message_id": message_id,
                    "penalty_applied": False,
                    "prompt_score": fallback.get("prompt_score"),
                    "sources": [],
                    "suggested_next_step": None,
                    "goal_progress": [],
                    "next_checkpoint": None,
                    "model": None,
                }
            )
            conversation.prompt_scores.append(int(fallback.get("prompt_score") or 5))
            conversation.touch()
            stored = self._sessions.store_idempotent(
                conversation_id, request.client_message_id, fallback
            )
            self._sessions.save_conversation(conversation_id, conversation)
            self._chat.track_result_metrics(stored)
            async for line in self._ndjson_stream_result(stored):
                yield line
            return

        prompt_text = "\n".join(str(m.get("content") or "") for m in chat_messages)
        tokens_used = self._llm.tokens_from_usage(usage, prompt_text, full_raw_response)

        final_result = process_model_response(
            full_raw_response,
            conversation,
            message_id=message_id,
            tokens_used=tokens_used,
            code_changed=code_changed,
            sources=sources,
            model=used_model,
        )

        self._chat.remember_goal_progress(conversation, final_result)
        self._chat.attach_checkpoint_coaching(conversation, final_result)
        self._chat.save_cache(conversation_id, request, final_result)
        stored_final = self._sessions.store_idempotent(
            conversation_id, request.client_message_id, final_result
        )
        self._sessions.save_conversation(conversation_id, conversation)
        self._chat.track_result_metrics(stored_final)

        yield json.dumps({"type": "final", **stored_final}, ensure_ascii=False) + "\n"
