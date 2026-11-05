import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
# OLD: from openai import RateLimitError
# Why: also need connection/timeout types registered as 503 handlers.
# Wrong: only RateLimitError was imported; other OpenAI outages escaped as 500.
# Better: import APIConnectionError + APITimeoutError and map them like LlmUnavailableError.
from openai import RateLimitError, APIConnectionError, APITimeoutError

from app.api.errors import (
    prelab_required_handler,
    token_budget_exceeded_handler,
    unknown_conversation_handler,
    unknown_message_handler,
    hint_reveal_forbidden_handler,
    ssrf_blocked_handler,
    llm_rate_limited_handler,
    llm_unavailable_handler,
)
from app.api.middleware import RequestIdMiddleware, JwtAuthMiddleware, RateLimitMiddleware
from app.api.routers import health, config, conversations, ui
from app.core.config import settings
from app.domain.exceptions import PrelabRequired, TokenBudgetExceeded, UnknownConversation, UnknownMessage, \
    HintRevealForbidden, SsrfBlockedError
# OLD: from app.infrastructure.llm_errors import LlmRateLimitError
# Why: new LlmUnavailableError covers post-retry connection/timeout failures.
# Wrong: rate-limit-only import left unavailable LLM as unhandled 500.
# Better: register both typed errors on the app.
from app.infrastructure.llm_errors import LlmRateLimitError, LlmUnavailableError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def purge_task():
        while True:
            try:
                await asyncio.sleep(5)
                deleted_count = conversations.get_session_service().purge_old_sessions()
                if deleted_count > 0:
                    # OLD: print(f"🧹 [Garbage Collector] Usunięto wygasłych sesji: {deleted_count}")
                    logger.info("Purged %s expired sessions", deleted_count)
            except Exception as e:
                # OLD: print(f"Błąd podczas sprzątania sesji: {e}")
                logger.exception("Session purge failed: %s", e)

    task = asyncio.create_task(purge_task())
    yield
    task.cancel()

def create_app() -> FastAPI:
    # OLD:
    # app = FastAPI(
    #     title="PJA-Sensei AI Module",
    #     version="0.1.0",
    #     lifespan=lifespan
    # )
    # Why: OpenAPI/Swagger is a free map of every admin/student endpoint.
    # Wrong: /docs always exposed even in locked-down deploys.
    # Better: docs/redoc/openapi only when AI_EXPOSE_DOCS=true.
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
    # Why: Spring calls AI server-to-server; browser CORS should be pinned if used at all.
    # Wrong: credentials=True with origins=["*"] is unsafe/ill-defined; methods/headers were wide open.
    # Better: empty origins deny browsers by default; never combine * with credentials; narrow methods/headers.
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
    # OLD: only the two handlers above — no LlmUnavailableError / APIConnectionError / APITimeoutError
    # Why: S1/lab demos returned raw 500 when Ollama was down — hard to explain to students/Spring.
    # Wrong: no stable message_id; clients could not distinguish “retry later” from app bugs.
    # Better: map to 503 llm_unavailable (and catch SDK errors that bypass our wrapper).
    app.add_exception_handler(LlmUnavailableError, llm_unavailable_handler)
    app.add_exception_handler(APIConnectionError, llm_unavailable_handler)
    app.add_exception_handler(APITimeoutError, llm_unavailable_handler)

    # OLD: always mount lab UI
    # app.include_router(ui.router)
    # Why: / and /scenarios are full API clients — unsafe if the AI port is reachable on campus Wi‑Fi.
    # Wrong: always-on UI expanded attack surface even with JWT on other routes.
    # Better: mount only when AI_EXPOSE_UI=true at process start (local .env for tests/dev).
    if settings.AI_EXPOSE_UI:
        app.include_router(ui.router)
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(conversations.router)

    return app
app = create_app()
