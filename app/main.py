import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.errors import prelab_required_handler, token_budget_exceeded_handler, unknown_conversation_handler, \
    unknown_message_handler
from app.api.routers import health, config, conversations
from app.core.config import settings
from app.domain.exceptions import PrelabRequired, TokenBudgetExceeded, UnknownConversation, UnknownMessage


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def purge_task():
        while True:
            try:
                await asyncio.sleep(5)
                deleted_count = conversations.get_session_service().purge_old_sessions()
                if deleted_count > 0:
                    print(f"🧹 [Garbage Collector] Usunięto wygasłych sesji: {deleted_count}")
            except Exception as e:
                print(f"Błąd podczas sprzątania sesji: {e}")

    task = asyncio.create_task(purge_task())
    yield
    task.cancel()

def create_app() -> FastAPI:
    app = FastAPI(
        title="PJA-Sensei AI Module",
        version="0.1.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(PrelabRequired, prelab_required_handler)
    app.add_exception_handler(TokenBudgetExceeded, token_budget_exceeded_handler)
    app.add_exception_handler(UnknownConversation, unknown_conversation_handler)
    app.add_exception_handler(UnknownMessage, unknown_message_handler)

    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(conversations.router)

    return app
app = create_app()