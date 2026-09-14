"""In-memory ConversationRepository — process-local session store."""

from __future__ import annotations

from collections.abc import Iterator
from threading import Lock

from app.domain.conversation import Conversation


class InMemoryConversationRepository:
    """Adapter pamięciowy: klucz = conversation_id (sesja nie ma pola id na agregacie)."""

    def __init__(self) -> None:
        self._by_id: dict[str, Conversation] = {}
        self._lock = Lock()

    def get(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            return self._by_id.get(conversation_id)

    def add(self, conversation_id: str, conversation: Conversation) -> None:
        with self._lock:
            if conversation_id in self._by_id:
                raise ValueError(f"Conversation with id {conversation_id} already exists")
            self._by_id[conversation_id] = conversation

    def save(self, conversation_id: str, conversation: Conversation) -> None:
        with self._lock:
            self._by_id[conversation_id] = conversation

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            return self._by_id.pop(conversation_id, None) is not None

    def items(self) -> Iterator[tuple[str, Conversation]]:
        with self._lock:
            return iter(list(self._by_id.items()))

    def __len__(self) -> int:
        with self._lock:
            return len(self._by_id)
