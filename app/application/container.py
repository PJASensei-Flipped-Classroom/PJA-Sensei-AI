from __future__ import annotations

from app.adapters.cache_memory import ExactMatchCache
from app.adapters.llm_openrouter import OpenRouterClient
from app.adapters.rag_chroma import RagService
from app.adapters.security import SecurityService
from app.application.analytics import AnalyticsService
from app.application.chat import ChatService
from app.application.goals import GoalsService
from app.application.prelab import PrelabService
from app.application.review import ReviewService
from app.application.sessions import SessionService
from app.application.stream import StreamService
from app.application.summary import SummaryService
from app.domain.conversation import Conversation


class AppContainer:
    def __init__(self) -> None:
        self.llm = OpenRouterClient()
        self.client = self.llm.client
        self.conversations: dict[str, Conversation] = {}
        self.rag = RagService()
        self.cache = ExactMatchCache()
        self.security = SecurityService()

        self.sessions = SessionService(self)
        self.chat = ChatService(self)
        self.stream = StreamService(self)
        self.prelab = PrelabService(self)
        self.goals = GoalsService(self)
        self.review = ReviewService(self)
        self.summary = SummaryService(self)
        self.analytics = AnalyticsService(self)
