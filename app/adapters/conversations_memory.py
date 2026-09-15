"""Lokalne repozytorium sesji konwersacji przechowywane w pamięci procesu."""

from __future__ import annotations

from collections.abc import Iterator
from threading import Lock

from app.domain.conversation import Conversation


class InMemoryConversationRepository:
    """Wątkowo-bezpieczny magazyn in-memory mapujący identyfikator na agregat Conversation."""

    def __init__(self) -> None:
        self._sessions: dict[str, Conversation] = {}
        self._lock = Lock()

    def get(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            return self._sessions.get(conversation_id)

    def add(self, conversation_id: str, conversation: Conversation) -> None:
        with self._lock:
            if conversation_id in self._sessions:
                raise ValueError(f"Conversation with id '{conversation_id}' already exists")
            self._sessions[conversation_id] = conversation

    def save(self, conversation_id: str, conversation: Conversation) -> None:
        """Wstawia nową sesję lub nadpisuje istniejącą (operacja upsert)."""
        with self._lock:
            self._sessions[conversation_id] = conversation

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(conversation_id, None) is not None

    def items(self) -> Iterator[tuple[str, Conversation]]:
        """Zwraca iterator po migawce (snapshot) bieżących elementów, chroniąc przed błędami współbieżności."""
        with self._lock:
            return iter(list(self._sessions.items()))

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)