from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Iterator
from pydantic import BaseModel
from app.domain.conversation import Conversation
from app.domain.sensei import ReferenceMaterial


class LlmResult(BaseModel):
    raw_content: str
    tokens_used: int
    model: str
    debug_info: Optional[Dict[str, Any]] = None

class RagChunk(BaseModel):
    title: str
    link: str
    snippet: str

class ConversationRepository(ABC):
    @abstractmethod
    def save(self, conversation: Conversation) -> None: pass

    @abstractmethod
    def get(self, conversation_id: str) -> Optional[Conversation]: pass

    @abstractmethod
    def delete(self, conversation_id: str) -> bool: pass

    @abstractmethod
    def purge_expired(self, ttl_seconds: int) -> int: pass

class LlmPort(ABC):
    @abstractmethod
    def generate_json(self, system_prompt: str, messages: List[Dict[str, str]]) -> LlmResult:
        pass

    def stream_json(self, system_prompt: str, messages: List[Dict[str, str]], model_override: Optional[str] = None) -> Iterator[str]:
        result = self.generate_json(system_prompt, messages, model_override=model_override)
        yield result.raw_content

    @abstractmethod
    def is_configured(self) -> bool:
        pass

class RagPort(ABC):
    @abstractmethod
    def ingest(self, conversation_id: str, materials: List[ReferenceMaterial]) -> int:
        pass

    @abstractmethod
    def retrieve(self, conversation_id: str, query: str, top_k: int = 3) -> List[RagChunk]:
        pass

    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> None:
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        pass


class CachePort(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[LlmResult]:
        pass

    @abstractmethod
    def set(self, key: str, value: LlmResult) -> None:
        pass

    @abstractmethod
    def size(self) -> int:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

class WebhookPort(ABC):
    @abstractmethod
    def send_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        pass