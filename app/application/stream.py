from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.api.schemas.requests import MessageRequest
from app.application.response_pipeline import (
    IncrementalAnswerExtractor,
    llm_error_fallback,
    process_model_response,
)
from app.core.metrics import metrics

if TYPE_CHECKING:
    from app.application.container import AppContainer

STREAM_CHUNK_SIZE = 40
logger = logging.getLogger(__name__)


class StreamService:
    def __init__(self, app: AppContainer) -> None:
        self._app = app

    async def stream_message(
        self, conversation_id: str, request: MessageRequest, message_id: str
    ):
        """Live NDJSON: token deltas as the model writes ``answer``, then a final payload."""
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        self._app.sessions.ensure_prelab_passed(conversation)
        self._app.sessions.ensure_token_budget(conversation)

        lang = conversation.config.language
        was_frustrated = conversation.is_frustrated

        prior = self._app.sessions.lookup_idempotent(
            conversation_id, request.client_message_id
        )
        if prior:
            self._app.chat._track_result_metrics(prior)
            async for line in self._ndjson_stream_result(prior):
                yield line
            return

        cached = self._app.chat._try_cache(
            conversation, conversation_id, request, message_id
        )
        if cached:
            cached = self._app.sessions.store_idempotent(
                conversation_id, request.client_message_id, cached
            )
            self._app.chat._track_result_metrics(cached)
            async for line in self._ndjson_stream_result(cached):
                yield line
            return

        chat_messages, code_changed, sources = await self._app.chat._prepare_chat_context(
            conversation_id, request
        )
        gen = self._app.chat._gen_kwargs(conversation)

        full_raw_response = ""
        usage = None
        extractor = IncrementalAnswerExtractor()

        async def _emit_live_from_stream(response_iter):
            nonlocal full_raw_response, usage
            async for chunk in response_iter:
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                if not chunk.choices:
                    continue
                piece = chunk.choices[0].delta.content or ""
                if not piece:
                    continue
                full_raw_response += piece
                delta = extractor.feed(piece)
                if delta:
                    yield json.dumps(
                        {"type": "token", "text": delta}, ensure_ascii=False
                    ) + "\n"

        try:
            response = await self._app.client.chat.completions.create(
                model=self._app.llm.model_for(conversation),
                messages=chat_messages,
                temperature=gen["temperature"],
                presence_penalty=gen["presence_penalty"],
                frequency_penalty=gen["frequency_penalty"],
                max_tokens=gen["max_tokens"],
                stream=True,
                stream_options={"include_usage": True},
                response_format=gen["response_format"],
            )
            async for line in _emit_live_from_stream(response):
                yield line
        except TypeError:
            try:
                response = await self._app.client.chat.completions.create(
                    model=self._app.llm.model_for(conversation),
                    messages=chat_messages,
                    temperature=gen["temperature"],
                    presence_penalty=gen["presence_penalty"],
                    frequency_penalty=gen["frequency_penalty"],
                    max_tokens=gen["max_tokens"],
                    stream=True,
                    response_format=gen["response_format"],
                )
                async for line in _emit_live_from_stream(response):
                    yield line
            except Exception as e:
                metrics.inc("llm_errors")
                logger.error("Stream LLM error: %s", e)
                fallback = llm_error_fallback(message_id, lang)
                async for line in self._ndjson_stream_result(fallback):
                    yield line
                return
        except Exception as e:
            metrics.inc("llm_errors")
            logger.error("Stream LLM error: %s", e)
            fallback = llm_error_fallback(message_id, lang)
            async for line in self._ndjson_stream_result(fallback):
                yield line
            return

        prompt_text = "\n".join(str(m.get("content") or "") for m in chat_messages)
        tokens_used = self._app.llm.tokens_from_usage(
            usage, prompt_text, full_raw_response
        )
        final_result = process_model_response(
            full_raw_response,
            conversation,
            message_id=message_id,
            tokens_used=tokens_used,
            code_changed=code_changed,
            was_frustrated=was_frustrated,
            sources=sources,
        )
        self._app.chat.remember_goal_progress(conversation, final_result)
        self._app.chat._save_cache(conversation_id, request, final_result)
        final_result = self._app.sessions.store_idempotent(
            conversation_id, request.client_message_id, final_result
        )
        self._app.chat._track_result_metrics(final_result)
        yield json.dumps({"type": "final", **final_result}, ensure_ascii=False) + "\n"

    async def _ndjson_stream_result(self, result: dict):
        """Replay helper for cache / errors (instant fake stream + final)."""
        answer = str(result.get("answer") or "")
        for i in range(0, len(answer), STREAM_CHUNK_SIZE):
            piece = answer[i : i + STREAM_CHUNK_SIZE]
            yield json.dumps({"type": "token", "text": piece}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "final", **result}, ensure_ascii=False) + "\n"
