from typing import Dict, Optional
from datetime import datetime, timezone
from app.domain.conversation import Conversation
from app.domain.ports import ConversationRepository

class InMemoryConversationRepository(ConversationRepository):
    def __init__(self):
        self._store: Dict[str, Conversation] = {}

    def save(self, conversation: Conversation) -> None:
        self._store[conversation.id] = conversation

    def get(self, conversation_id: str) -> Optional[Conversation]:
        conv = self._store.get(conversation_id)
        if conv:
            conv.touch()
        return conv

    def delete(self, conversation_id: str) -> bool:
        if conversation_id in self._store:
            del self._store[conversation_id]
            return True
        return False

    def purge_expired(self, ttl_seconds: int) -> int:
        now = datetime.now(timezone.utc)
        to_delete = [
            cid for cid, conv in self._store.items()
            if (now - conv.last_activity).total_seconds() > ttl_seconds
        ]
        for cid in to_delete:
            del self._store[cid]
        return len(to_delete)

    def count(self) -> int:
        return len(self._store)