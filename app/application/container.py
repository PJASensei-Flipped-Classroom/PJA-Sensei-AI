"""Composition root — wires adapters to use-cases and manages application lifecycle."""

from __future__ import annotations

import logging

from app.adapters.cache_memory import ExactMatchCache
from app.adapters.conversations_memory import InMemoryConversationRepository
from app.adapters.llm_openai import OpenAICompatibleClient
from app.adapters.rag_chroma import RagService
from app.adapters.security import SecurityService
from app.application.chat import ChatService
from app.application.prelab import PrelabService
from app.application.sessions import SessionService
from app.application.stream import StreamService
from app.application.summary import SummaryService

logger = logging.getLogger(__name__)


class AppContainer:
    """Główny kontener IoC zarządzający grafem zależności i cyklem życia zasobów."""

    def __init__(
        self,
        *,
        conversations_repo: InMemoryConversationRepository | None = None,
        llm_client: OpenAICompatibleClient | None = None,
        rag_service: RagService | None = None,
        cache_service: ExactMatchCache | None = None,
        security_service: SecurityService | None = None,
    ) -> None:
        # 1. Adaptery infrastrukturalne (umożliwiają łatwe podstawienie mocków w testach)
        self.conversations = conversations_repo or InMemoryConversationRepository()
        self.llm = llm_client or OpenAICompatibleClient()
        self.rag = rag_service or RagService()
        self.cache = cache_service or ExactMatchCache()
        self.security = security_service or SecurityService()

        # Test monkeypatch alias (OpenAI AsyncOpenAI surface)
        self.client = self.llm.client

        # 2. Warstwa logiki biznesowej i przypadków użycia
        self.sessions = SessionService(self.conversations, self.rag)
        self.chat = ChatService(self.sessions, self.llm, self.rag, self.cache)
        self.stream = StreamService(self.sessions, self.chat, self.llm)
        self.prelab = PrelabService(self.sessions)
        self.summary = SummaryService(self.sessions, self.llm)

        # 3. Rozwiązanie zależności cyklicznej
        self.sessions.bind_summary(self.summary)

    async def close(self) -> None:
        """Bezpieczne zwalnianie puli połączeń i zasobów podczas zamykania serwera."""
        from app.adapters.webhooks import close_telemetry_client

        logger.info("Zamykanie zasobów kontenera aplikacji...")
        if hasattr(self.llm, "close"):
            await self.llm.close()
        await close_telemetry_client()