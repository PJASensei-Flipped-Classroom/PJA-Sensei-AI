from typing import Optional

from fastapi import Depends

from app.application.chat_service import ChatService
from app.application.prelab_service import PrelabService
from app.application.session_service import SessionService
from app.core.config import settings
from app.domain.ports import CachePort, LlmPort, RagPort, WebhookPort
from app.infrastructure.cache_memory import InMemoryLruCache
from app.infrastructure.conversations_memory import InMemoryConversationRepository
from app.infrastructure.llm_openai import OpenAiCompatibleLlmAdapter
from app.infrastructure.rag_chroma import ChromaRagAdapter
from app.infrastructure.webhooks import HttpWebhookAdapter

rag_adapter = ChromaRagAdapter()
llm_cache = InMemoryLruCache(max_size=settings.CACHE_SIZE, ttl_seconds=settings.CACHE_TTL_SECONDS)
llm_adapter = OpenAiCompatibleLlmAdapter()

repo = InMemoryConversationRepository()
webhook_adapter = HttpWebhookAdapter()


def get_prelab_service() -> PrelabService:
    return PrelabService(repo)


def get_webhook_port() -> WebhookPort:
    return webhook_adapter


def get_llm_port() -> LlmPort:
    return llm_adapter


def get_rag_port() -> RagPort:
    return rag_adapter


def get_cache_port() -> CachePort:
    return llm_cache


# OLD: lifespan called get_session_service() with no args (Depends objects as rag/webhooks).
# Removed because: build_session_service() wires real adapters for background purge.
def build_session_service(
    rag: Optional[RagPort] = None,
    webhooks: Optional[WebhookPort] = None,
) -> SessionService:
    return SessionService(
        repo=repo,
        rag=rag if rag is not None else rag_adapter,
        webhooks=webhooks if webhooks is not None else webhook_adapter,
    )


def get_session_service(
    rag: RagPort = Depends(get_rag_port),
    webhooks: WebhookPort = Depends(get_webhook_port),
) -> SessionService:
    return build_session_service(rag=rag, webhooks=webhooks)


def get_chat_service(
    svc: SessionService = Depends(get_session_service),
    llm: LlmPort = Depends(get_llm_port),
    rag: RagPort = Depends(get_rag_port),
    cache: CachePort = Depends(get_cache_port),
    webhooks: WebhookPort = Depends(get_webhook_port),
) -> ChatService:
    return ChatService(repo=repo, session_svc=svc, llm=llm, rag=rag, cache=cache, webhooks=webhooks)
