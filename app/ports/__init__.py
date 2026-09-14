"""Domain and application ports (Protocols) for hexagonal architecture decoupling."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable

from app.domain.conversation import Conversation
from app.domain.sensei import ReferenceMaterial


@runtime_checkable
class ConversationRepository(Protocol):
    """Port repozytorium agregatu Conversation."""

    def get(self, conversation_id: str) -> Conversation | None: ...

    def add(self, conversation_id: str, conversation: Conversation) -> None: ...

    def save(self, conversation_id: str, conversation: Conversation) -> None: ...

    def delete(self, conversation_id: str) -> bool: ...

    def items(self) -> Iterator[tuple[str, Conversation]]: ...

    def __len__(self) -> int: ...


@runtime_checkable
class LlmPort(Protocol):
    """Port komunikacji z dostawcą modelu językowego."""

    def model_for(self, conversation: Conversation) -> str: ...

    def tokens_from_usage(self, usage: Any, *text_parts: str) -> int: ...

    async def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Any: ...


@runtime_checkable
class RagPort(Protocol):
    """Port bazy wiedzy i silnika wyszukiwania wektorowego."""

    def retrieve_context(
        self, conversation_id: str, question: str, lang: str = "pl"
    ) -> tuple[str, list[dict[str, Any]]]: ...

    def delete_conversation_data(self, conversation_id: str) -> None: ...

    async def load_materials(
        self, conversation_id: str, reference_materials: list[ReferenceMaterial]
    ) -> None: ...

    def chroma_ok(self) -> bool: ...


@runtime_checkable
class CachePort(Protocol):
    """Port pamięci podręcznej powtarzalnych zapytań."""

    def get_cached_response(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
    ) -> dict[str, Any] | None: ...

    def save_to_cache(
        self,
        conversation_id: str,
        question: str,
        error_logs: str | None,
        current_code: str,
        response_data: dict[str, Any],
    ) -> None: ...

    @property
    def size(self) -> int: ...


@runtime_checkable
class SecurityPort(Protocol):
    """Port analizy bezpieczeństwa i detekcji ataków prompt injection."""

    async def is_prompt_safe(self, user_input: str) -> bool: ...

    def injection_blocked_response(self, language: str) -> dict[str, Any]: ...


@runtime_checkable
class SummaryPort(Protocol):
    """Port serwisu ewaluacji i raportowania wyników studenta."""

    async def generate_summary(self, conversation_id: str) -> dict[str, Any]: ...