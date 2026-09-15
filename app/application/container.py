"""Główny korzeń kompozycji (Composition Root): rejestracja adapterów, serwisów i cyklu życia zasobów."""

from __future__ import annotations

import logging
from typing import Any

from app.adapters.cache_memory import ExactMatchCache
from app.adapters.conversations_memory import InMemoryConversationRepository
from app.adapters.llm_openai import OpenAICompatibleClient
from app.adapters.rag_chroma import RagService
from app.adapters.security import SecurityService
from app.adapters.webhooks import close_telemetry_client
from app.application.chat import ChatService
from app.application.prelab import PrelabService
from app.application.sessions import SessionService
from app.application.stream import StreamService
from app.application.summary import SummaryService
from app.ports import CachePort, ConversationRepository, LlmPort, RagPort, SecurityPort

logger = logging.getLogger(__name__)


class AppContainer:
    """Kontener Dependency Injection (IoC) zarządzający grafem obiektów i zwalnianiem zasobów I/O."""

    def __init__(
        self,
        *,
        conversations_repo: ConversationRepository | None = None,
        llm_client: LlmPort | None = None,
        rag_service: RagPort | None = None,
        cache_service: CachePort | None = None,
        security_service: SecurityPort | None = None,
    ) -> None:
        # 1. Inicjalizacja warstwy infrastruktury (adaptery) z możliwością wstrzyknięcia mocków
        self.conversations = conversations_repo or InMemoryConversationRepository()
        self.llm = llm_client or OpenAICompatibleClient()
        self.rag = rag_service or RagService()
        self.cache = cache_service or ExactMatchCache()
        llm_http = getattr(self.llm, "client", None)
        self.security = security_service or SecurityService(client=llm_http)

        # Alias ułatwiający testowanie i monkeypatchowanie klienta OpenAI
        self.client = llm_http

        # 2. Inicjalizacja serwisów aplikacyjnych (przypadki użycia)
        self.sessions = SessionService(self.conversations, self.rag)
        self.chat = ChatService(self.sessions, self.llm, self.rag, self.cache)
        self.stream = StreamService(self.sessions, self.chat, self.llm)
        self.prelab = PrelabService(self.sessions)
        self.summary = SummaryService(self.sessions, self.llm)

        # 3. Rozwiązanie zależności cyklicznej między sesjami a podsumowaniami
        self.sessions.bind_summary(self.summary)

    async def close(self) -> None:
        """Asynchronicznie zwalnia pule połączeń HTTP, sesje i zasoby sieciowe."""
        logger.info("Zamykanie zasobów sieciowych kontenera aplikacji...")

        if close_sec := getattr(self.security, "close", None):
            await close_sec()

        # Bezpieczne zamykanie klienta LLM, jeśli implementuje metodę close/aclose
        if close_fn := getattr(self.llm, "close", None):
            await close_fn()

        # Zamknięcie współdzielonej puli połączeń dla webhooków telemetrycznych
        await close_telemetry_client()

    async def __aenter__(self) -> AppContainer:
        """Wsparcie dla użycia kontenera w asynchronicznym menedżerze kontekstu."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Gwarantowane zwolnienie zasobów po wyjściu z bloku async with."""
        await self.close()