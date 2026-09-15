"""FastAPI application factory and middleware wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import enforce_rate_limit
from app.api.errors import register_exception_handlers
from app.api.middleware import RequestIdMiddleware
from app.api.routers import (
    config_validate,
    conversations,
    health,
    messages,
    prelab,
)
from app.application.container import AppContainer
from app.core.auth import require_auth
from app.core.config import CORS_ORIGINS
from app.core.rate_limit import start_rate_limit_cleanup, stop_rate_limit_cleanup

logger = logging.getLogger(__name__)


def create_app(container: AppContainer | None = None) -> FastAPI:
    """Tworzy i konfiguruje kompletną instancję aplikacji FastAPI."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # 1. Start serwera: wstrzyknięcie kontenera zależności
        app.state.container = container or AppContainer()
        start_rate_limit_cleanup()
        logger.info("Kontener aplikacji został pomyślnie zainicjalizowany.")
        try:
            yield
        finally:
            stop_rate_limit_cleanup()
            await app.state.container.close()
            logger.info("Zasoby kontenera aplikacji zostały zwolnione.")

    app = FastAPI(
        title="PJA-Sensei AI Microservice",
        version="1.0.0",
        description="Sokratyczny asystent dydaktyczny dla laboratoriów programistycznych.",
        lifespan=lifespan,
    )

    # Rejestracja middleware'ów (kolejność wykonania: RequestId -> CORS)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        expose_headers=["X-Message-Id", "X-Request-Id"],
    )

    # Rejestracja globalnych translatorów wyjątków domenowych na kody HTTP
    register_exception_handlers(app)

    # 1. Trasy publiczne (Healthchecks, Metryki, Readiness)
    app.include_router(health.router)

    # 2. Trasy chronione (Autoryzacja JWT + Limit zapytań)
    protected = APIRouter(
        dependencies=[Depends(require_auth), Depends(enforce_rate_limit)]
    )

    protected.include_router(config_validate.router)
    protected.include_router(conversations.router)
    protected.include_router(messages.router)
    protected.include_router(prelab.router)

    app.include_router(protected)

    return app


app = create_app()