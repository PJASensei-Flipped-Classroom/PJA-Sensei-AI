"""OpenRouter / OpenAI-compatible LLM client helpers."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion

from app.core.config import MAIN_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from app.domain.conversation import Conversation

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Odporny na błędy klient asynchroniczny dla modeli OpenAI/OpenRouter."""

    def __init__(
        self,
        base_url: str = OPENROUTER_BASE_URL,
        api_key: str = OPENROUTER_API_KEY,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    @property
    def client(self) -> AsyncOpenAI:
        """Expose AsyncOpenAI for tests / monkeypatch."""
        return self._client

    async def close(self) -> None:
        """Zwalnia pulę połączeń HTTP."""
        await self._client.close()

    async def __aenter__(self) -> OpenRouterClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def model_for(self, conversation: Conversation) -> str:
        """Wybiera skonfigurowany model dla danej sesji lub stosuje fallback."""
        # Bezpieczny odczyt atrybutu camelCase lub snake_case
        agent_config = getattr(conversation.config, "agent_behavior", None) or getattr(
            conversation.config, "agentBehavior", None
        )
        custom_model = getattr(agent_config, "model", None) if agent_config else None
        return custom_model or MAIN_MODEL

    @staticmethod
    def tokens_from_usage(
        usage: CompletionUsage | dict[str, Any] | None,
        *text_parts: str,
    ) -> int:
        """Wyznacza liczbę tokenów na podstawie odpowiedzi lub heurystyki znakowej."""
        if usage:
            if isinstance(usage, dict):
                total = usage.get("total_tokens")
                prompt = usage.get("prompt_tokens", 0) or 0
                completion = usage.get("completion_tokens", 0) or 0
            else:
                total = getattr(usage, "total_tokens", None)
                prompt = getattr(usage, "prompt_tokens", 0) or 0
                completion = getattr(usage, "completion_tokens", 0) or 0

            if total:
                return int(total)
            if prompt or completion:
                return int(prompt) + int(completion)

        # Plan awaryjny (heurystyka ~4 znaki na token)
        chars = sum(len(t or "") for t in text_parts)
        return max(1, chars // 4)

    async def create_chat_completion(
        self,
        messages: Sequence[dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ChatCompletion:
        """Wysyła zapytanie chat completion z jawnym typowaniem i obsługą błędów."""
        try:
            return await self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                **kwargs,
            )
        except RateLimitError as e:
            logger.error("Przekroczono rate limit dostawcy LLM: %s", e)
            raise
        except APITimeoutError as e:
            logger.error("Upłynął limit czasu zapytania do LLM: %s", e)
            raise
        except APIError as e:
            logger.error("Błąd API OpenRouter/OpenAI: status=%s, msg=%s", e.status_code, e.message)
            raise