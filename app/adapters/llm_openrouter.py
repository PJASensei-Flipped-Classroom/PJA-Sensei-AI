"""OpenRouter / OpenAI-compatible LLM client helpers."""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from app.core.config import MAIN_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from app.domain.conversation import Conversation


class OpenRouterClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )

    def model_for(self, conversation: Conversation) -> str:
        return conversation.config.agentBehavior.model or MAIN_MODEL

    @staticmethod
    def tokens_from_usage(usage: Any, *text_parts: str) -> int:
        if usage is not None:
            total = getattr(usage, "total_tokens", None)
            if total:
                return int(total)
            prompt = getattr(usage, "prompt_tokens", 0) or 0
            completion = getattr(usage, "completion_tokens", 0) or 0
            if prompt or completion:
                return int(prompt) + int(completion)
        chars = sum(len(t or "") for t in text_parts)
        return max(1, chars // 4)
