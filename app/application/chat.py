from __future__ import annotations

import difflib
import json
import logging
import re
import uuid
from typing import TYPE_CHECKING

from openai.types.chat import ChatCompletionMessageParam

from app.api.schemas.requests import MessageRequest, RevealHintRequest
from app.application.prompts import (
    build_system_prompt,
    format_code_context_block,
    generation_params,
)
from app.application.response_pipeline import (
    collect_identifier_tokens,
    contains_revealed_code,
    compress_history,
    format_pinned_identifiers_note,
    llm_error_fallback,
    process_model_response,
)
from app.core.metrics import metrics
from app.domain.conversation import Conversation, consecutive_low_enough
from app.domain.exceptions import RevealNotAllowed
from app.domain.sensei import CodeContext

if TYPE_CHECKING:
    from app.application.container import AppContainer

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, app: AppContainer) -> None:
        self._app = app

    async def _prepare_chat_context(
        self,
        conversation_id: str,
        request: MessageRequest,
        *,
        append_user: bool = True,
    ) -> tuple[list[ChatCompletionMessageParam], bool, list[dict]]:
        conversation = self._app.conversations[conversation_id]
        lang = conversation.config.language
        conversation.touch()

        rag_context, sources = self._app.rag.retrieve_context(
            conversation_id, request.question
        )
        code_diff_text = ""
        code_changed = False

        if conversation.last_code and conversation.last_code != request.code_context.current_code:
            code_changed = True
            diff = "\n".join(
                difflib.unified_diff(
                    conversation.last_code.splitlines(),
                    request.code_context.current_code.splitlines(),
                    lineterm="",
                )
            )
            code_diff_text = (
                f"\nChanges made by student since last prompt:\n```diff\n{diff}\n```\n"
                if lang == "en"
                else f"\nZmiany w kodzie wprowadzone przez studenta od ostatniej porady:\n```diff\n{diff}\n```\n"
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
        history_compressed = compress_history(history_clean, language=lang)
        system_prompt = build_system_prompt(conversation)
        task_label = "Main assignment:" if lang == "en" else "Zadanie główne:"

        chat_messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"{task_label} {conversation.problem}"},
        ]
        pinned_note = format_pinned_identifiers_note(
            conversation.pinned_identifiers, lang
        )
        if pinned_note:
            chat_messages.append({"role": "system", "content": pinned_note})
        chat_messages.extend(history_compressed)
        return chat_messages, code_changed, sources

    def _try_cache(
        self,
        conversation: Conversation,
        conversation_id: str,
        request: MessageRequest,
        message_id: str | None = None,
    ) -> dict | None:
        if conversation.is_frustrated:
            return None

        cached = self._app.cache.get_cached_response(
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
        if message_id is not None:
            result["message_id"] = message_id

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
            }
        )
        debug = dict(result.get("debug_info") or {})
        debug["is_frustrated"] = conversation.is_frustrated
        result["debug_info"] = debug
        return result

    def _save_cache(
        self,
        conversation_id: str,
        request: MessageRequest,
        final_result: dict,
    ) -> None:
        self._app.cache.save_to_cache(
            conversation_id,
            request.question,
            request.code_context.error_logs,
            request.code_context.current_code,
            final_result,
        )

    def _track_result_metrics(self, result: dict) -> None:
        metrics.inc("messages_total")
        metrics.inc("tokens_total", int(result.get("tokens_used") or 0))
        if result.get("penalty_applied"):
            metrics.inc("penalties_total")

    def remember_goal_progress(self, conversation: Conversation, result: dict) -> None:
        progress = result.get("goal_progress") or []
        if progress:
            conversation.goal_progress = list(progress)
            done = {g.get("goal") for g in progress if g.get("status") == "done"}
            for cp in conversation.config.checkpoints:
                if cp.after_goal in done and cp.id not in conversation.unlocked_checkpoints:
                    conversation.unlocked_checkpoints.append(cp.id)

    def _gen_kwargs(self, conversation: Conversation) -> dict:
        params = generation_params(conversation.config.agentBehavior.mode or "debug")
        return {
            "temperature": params["temperature"],
            "presence_penalty": 0.6,
            "frequency_penalty": 0.4,
            "max_tokens": params["max_tokens"],
            "response_format": {"type": "json_object"},
        }

    async def send_message(self, conversation_id: str, request: MessageRequest) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        self._app.sessions.ensure_prelab_passed(conversation)
        self._app.sessions.ensure_token_budget(conversation)

        prior = self._app.sessions.lookup_idempotent(
            conversation_id, request.client_message_id
        )
        if prior:
            self._track_result_metrics(prior)
            return prior

        was_frustrated = conversation.is_frustrated
        cached = self._try_cache(conversation, conversation_id, request)
        if cached:
            cached = self._app.sessions.store_idempotent(
                conversation_id, request.client_message_id, cached
            )
            self._track_result_metrics(cached)
            return cached

        chat_messages, code_changed, sources = await self._prepare_chat_context(
            conversation_id, request
        )

        try:
            response = await self._app.client.chat.completions.create(
                model=self._app.llm.model_for(conversation),
                messages=chat_messages,
                **self._gen_kwargs(conversation),
            )
            raw_content = response.choices[0].message.content or ""
            prompt_text = "\n".join(str(m.get("content") or "") for m in chat_messages)
            tokens_used = self._app.llm.tokens_from_usage(
                response.usage, prompt_text, raw_content
            )
        except Exception as e:
            metrics.inc("llm_errors")
            logger.error("Error calling LLM API: %s", e)
            message_id = str(uuid.uuid4())
            return llm_error_fallback(message_id, conversation.config.language)

        message_id = str(uuid.uuid4())
        final_result = process_model_response(
            raw_content,
            conversation,
            message_id=message_id,
            tokens_used=tokens_used,
            code_changed=code_changed,
            was_frustrated=was_frustrated,
            sources=sources,
        )
        self.remember_goal_progress(conversation, final_result)
        self._save_cache(conversation_id, request, final_result)
        final_result = self._app.sessions.store_idempotent(
            conversation_id, request.client_message_id, final_result
        )
        self._track_result_metrics(final_result)
        return final_result

    async def regenerate_message(
        self, conversation_id: str, message_id: str
    ) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        self._app.sessions.ensure_prelab_passed(conversation)
        self._app.sessions.ensure_token_budget(conversation)

        idx = next(
            (
                i
                for i, m in enumerate(conversation.messages)
                if m.get("message_id") == message_id and m.get("role") == "assistant"
            ),
            None,
        )
        if idx is None:
            raise KeyError("message_not_found")
        if idx == 0 or conversation.messages[idx - 1].get("role") != "user":
            raise KeyError("user_context_missing")

        conversation.messages.pop(idx)
        if conversation.prompt_scores:
            conversation.prompt_scores.pop()

        user_content = conversation.messages[idx - 1]["content"]
        q_match = re.search(
            r"(?:Student question|Pytanie studenta):\s*(.*)$",
            user_content,
            re.MULTILINE,
        )
        question = q_match.group(1).strip() if q_match else "Please continue."
        request = MessageRequest(
            question=question,
            code_context=CodeContext(
                current_file_name="unknown",
                current_code=conversation.last_code,
                error_logs="",
            ),
        )

        was_frustrated = conversation.is_frustrated
        chat_messages, code_changed, sources = await self._prepare_chat_context(
            conversation_id, request, append_user=False
        )
        try:
            gen = self._gen_kwargs(conversation)
            response = await self._app.client.chat.completions.create(
                model=self._app.llm.model_for(conversation),
                messages=chat_messages,
                temperature=min(0.9, gen["temperature"] + 0.1),
                presence_penalty=gen["presence_penalty"],
                frequency_penalty=gen["frequency_penalty"],
                max_tokens=gen["max_tokens"],
                response_format=gen["response_format"],
            )
            raw_content = response.choices[0].message.content or ""
            prompt_text = "\n".join(str(m.get("content") or "") for m in chat_messages)
            tokens_used = self._app.llm.tokens_from_usage(
                response.usage, prompt_text, raw_content
            )
        except Exception as e:
            metrics.inc("llm_errors")
            return llm_error_fallback(str(uuid.uuid4()), conversation.config.language)

        new_id = str(uuid.uuid4())
        result = process_model_response(
            raw_content,
            conversation,
            message_id=new_id,
            tokens_used=tokens_used,
            code_changed=code_changed,
            was_frustrated=was_frustrated,
            sources=sources,
        )
        self.remember_goal_progress(conversation, result)
        self._track_result_metrics(result)
        return result

    async def reveal_hint(
        self, conversation_id: str, payload: RevealHintRequest
    ) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        self._app.sessions.ensure_prelab_passed(conversation)
        if not (
            conversation.is_frustrated
            or consecutive_low_enough(conversation.prompt_scores)
        ):
            raise RevealNotAllowed(
                "Reveal available only after sustained low scores / frustration"
            )

        lang = conversation.config.language
        code = (
            payload.code_context.current_code
            if payload.code_context
            else conversation.last_code
        )
        focus = payload.focus or ""
        prompt = f"""
You are a Socratic mentor giving ONE stronger unlocking hint (still NO full solution code).
Language: {"English" if lang == "en" else "Polish"}.
Assignment: {conversation.problem}
Student code:
{code}
Focus: {focus}

Return JSON: {{"hint": "...", "suggested_next_step": "..."}}
"""
        response = await self._app.client.chat.completions.create(
            model=self._app.llm.model_for(conversation),
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
        return {
            "message_id": message_id,
            "hint": hint,
            "suggested_next_step": data.get("suggested_next_step"),
            "reveal_count": conversation.reveal_count,
        }
