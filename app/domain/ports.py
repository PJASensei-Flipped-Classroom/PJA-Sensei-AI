from abc import ABC, abstractmethod
from typing import Optional
from app.domain.conversation import Conversation


class ConversationRepository(ABC):
    @abstractmethod
    def save(self, conversation: Conversation) -> None: pass

    @abstractmethod
    def get(self, conversation_id: str) -> Optional[Conversation]: pass

    @abstractmethod
    def delete(self, conversation_id: str) -> bool: pass

    @abstractmethod
    def purge_expired(self, ttl_seconds: int) -> int: pass