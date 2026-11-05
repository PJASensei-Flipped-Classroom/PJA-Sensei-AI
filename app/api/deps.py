"""Composition root: shared adapters and FastAPI dependencies."""
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
# In-memory only until a durable store is chosen with the Spring team.
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


def get_session_service(
    rag: RagPort = Depends(get_rag_port),
    webhooks: WebhookPort = Depends(get_webhook_port),
) -> SessionService:
    return SessionService(repo=repo, rag=rag, webhooks=webhooks)


def get_chat_service(
    svc: SessionService = Depends(get_session_service),
    llm: LlmPort = Depends(get_llm_port),
    rag: RagPort = Depends(get_rag_port),
    cache: CachePort = Depends(get_cache_port),
    webhooks: WebhookPort = Depends(get_webhook_port),
) -> ChatService:
    return ChatService(repo=repo, session_svc=svc, llm=llm, rag=rag, cache=cache, webhooks=webhooks)
