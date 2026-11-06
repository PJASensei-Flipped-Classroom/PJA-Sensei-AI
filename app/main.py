import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# OLD: from openai import RateLimitError
# Removed because: connection/timeout outages must map to 503 like LlmUnavailableError.
from openai import APIConnectionError, APITimeoutError, RateLimitError

# OLD: from app.api.routers import conversations; conversations.get_session_service()
# Removed because: router re-export passed bare Depends() objects outside FastAPI; use build_session_service().
from app.api.deps import build_session_service
from app.api.errors import (
    hint_reveal_forbidden_handler,
    llm_rate_limited_handler,
    llm_unavailable_handler,
    prelab_required_handler,
    ssrf_blocked_handler,
    token_budget_exceeded_handler,
    unknown_conversation_handler,
    unknown_message_handler,
)
from app.api.middleware import JwtAuthMiddleware, RateLimitMiddleware, RequestIdMiddleware
from app.api.routers import config, conversations, health, ui
from app.core.config import settings
from app.domain.exceptions import (
    HintRevealForbidden,
    PrelabRequired,
    SsrfBlockedError,
    TokenBudgetExceeded,
    UnknownConversation,
    UnknownMessage,
)
# OLD: from app.infrastructure.llm_errors import LlmRateLimitError
# Removed because: LlmUnavailableError covers post-retry connection/timeout failures.
from app.infrastructure.llm_errors import LlmRateLimitError, LlmUnavailableError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def purge_task():
        while True:
            try:
                await asyncio.sleep(5)
                deleted_count = build_session_service().purge_old_sessions()
                if deleted_count > 0:
                    # OLD: print(f"🧹 [Garbage Collector] Usunięto wygasłych sesji: {deleted_count}")
                    # Removed because: use structured logging instead of print in production.
                    logger.info("Purged %s expired sessions", deleted_count)
            except Exception as e:
                # OLD: print(f"Błąd podczas sprzątania sesji: {e}")
                # Removed because: logger.exception keeps stack traces without stdout spam.
                logger.exception("Session purge failed: %s", e)

    task = asyncio.create_task(purge_task())
    yield
    task.cancel()


def create_app() -> FastAPI:
    # OLD:
    # app = FastAPI(title="PJA-Sensei AI Module", version="0.1.0", lifespan=lifespan)
    # Removed because: /docs always exposed every admin/student route; gate behind AI_EXPOSE_DOCS.
    app = FastAPI(
        title="PJA-Sensei AI Module",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.AI_EXPOSE_DOCS else None,
        redoc_url="/redoc" if settings.AI_EXPOSE_DOCS else None,
        openapi_url="/openapi.json" if settings.AI_EXPOSE_DOCS else None,
    )

    # Middleware order: last added runs first on request.
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(JwtAuthMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # OLD:
    # app.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=settings.CORS_ORIGINS,
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    # )
    # Removed because: credentials=True with origins=["*"] is unsafe; Spring is server-to-server.
    origins = list(settings.CORS_ORIGINS or [])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(origins) and origins != ["*"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    )

    app.add_exception_handler(PrelabRequired, prelab_required_handler)
    app.add_exception_handler(TokenBudgetExceeded, token_budget_exceeded_handler)
    app.add_exception_handler(UnknownConversation, unknown_conversation_handler)
    app.add_exception_handler(UnknownMessage, unknown_message_handler)
    app.add_exception_handler(HintRevealForbidden, hint_reveal_forbidden_handler)
    app.add_exception_handler(SsrfBlockedError, ssrf_blocked_handler)
    app.add_exception_handler(LlmRateLimitError, llm_rate_limited_handler)
    app.add_exception_handler(RateLimitError, llm_rate_limited_handler)
    # OLD: only RateLimitError / LlmRateLimitError handlers above
    # Removed because: Ollama down returned raw 500; map transport errors to 503 llm_unavailable.
    app.add_exception_handler(LlmUnavailableError, llm_unavailable_handler)
    app.add_exception_handler(APIConnectionError, llm_unavailable_handler)
    app.add_exception_handler(APITimeoutError, llm_unavailable_handler)

    # OLD: app.include_router(ui.router)  # always mounted
    # Removed because: / and /scenarios are full API clients; mount only when AI_EXPOSE_UI=true.
    if settings.AI_EXPOSE_UI:
        app.include_router(ui.router)
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(conversations.router)

    return app


app = create_app()
