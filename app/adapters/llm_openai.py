"""Asynchroniczny klient LLM zgodny ze standardem OpenAI (np. Ollama, LM Studio)."""

from __future__ import annotations

from collections.abc import Sequence
import logging
from typing import Any

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion

from app.core.config import LLM_API_KEY, LLM_BASE_URL, MAIN_MODEL
from app.domain.conversation import Conversation

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:
    """Wątkowo i asynchronicznie bezpieczny wrapper na oficjalnego klienta AsyncOpenAI."""

    def __init__(
        self,
        base_url: str = LLM_BASE_URL,
        api_key: str = LLM_API_KEY,
        timeout: float = 120.0,
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
        """Udostępnia wewnętrzną instancję AsyncOpenAI (przydatne do testów jednostkowych i mockowania)."""
        return self._client

    async def close(self) -> None:
        """Zwalnia pulę połączeń klienta HTTP."""
        await self._client.close()

    async def __aenter__(self) -> OpenAICompatibleClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def model_for(self, conversation: Conversation) -> str:
        """Pobiera model przypisany do danej konwersacji lub stosuje domyślny fallback."""
        config = getattr(conversation, "config", None)
        agent = getattr(config, "agent_behavior", None) or getattr(config, "agentBehavior", None)
        return getattr(agent, "model", None) or MAIN_MODEL

    @staticmethod
    def tokens_from_usage(
        usage: CompletionUsage | dict[str, Any] | None,
        *text_parts: str,
    ) -> int:
        """Odczytuje liczbę zużytych tokenów lub szacuje ją heurystycznie (1 token ≈ 4 znaki)."""
        if usage is not None:
            # Ujednolicenie odczytu niezależnie od tego, czy dostaliśmy dict, czy obiekt Pydantic/OpenAI
            get_val = usage.get if isinstance(usage, dict) else lambda k, d=0: getattr(usage, k, d)

            total = get_val("total_tokens", None)
            if total:
                return int(total)

            prompt = get_val("prompt_tokens", 0) or 0
            completion = get_val("completion_tokens", 0) or 0
            if prompt or completion:
                return int(prompt) + int(completion)

        total_characters = sum(len(text or "") for text in text_parts)
        return max(1, total_characters // 4)

    async def create_chat_completion(
        self,
        messages: Sequence[dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> ChatCompletion:
        """Wysyła zapytanie chat completion z jawnym logowaniem wyjątków sieciowych i limitów API."""
        try:
            return await self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                **kwargs,
            )
        except RateLimitError as exc:
            logger.error("Przekroczono limit zapytań (Rate Limit) dostawcy LLM: %s", exc)
            raise
        except APITimeoutError as exc:
            logger.error("Upłynął limit czasu (Timeout) oczekiwania na odpowiedź LLM: %s", exc)
            raise
        except APIError as exc:
            http_code = getattr(exc, "status_code", None)
            detail = getattr(exc, "message", None) or str(exc)
            logger.error("Błąd API LLM [kod HTTP: %s]: %s", http_code, detail)
            raise