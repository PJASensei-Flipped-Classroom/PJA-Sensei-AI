from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Iterator
from pydantic import BaseModel
from app.domain.conversation import Conversation

class LlmResult(BaseModel):
    raw_content: str
    tokens_used: int
    model: str
    debug_info: Optional[Dict[str, Any]] = None

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