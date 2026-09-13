"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import enforce_rate_limit, init_container
from app.api.errors import register_exception_handlers
from app.api.middleware import RequestIdMiddleware
from app.api.routers import (
    analytics,
    config_validate,
    conversations,
    health,
    messages,
    prelab,
)
from app.application.container import AppContainer
from app.core.auth import require_auth
from app.core.config import CORS_ORIGINS

logger = logging.getLogger(__name__)


def create_app(container: AppContainer | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = container or init_container()
        logger.info("Application container initialized.")
        try:
            yield
        finally:
            shutdown = getattr(app.state.container, "shutdown", None)
            if callable(shutdown):
                await shutdown()

    app = FastAPI(
        title="PJA-Sensei AI Microservice",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        expose_headers=["X-Message-Id", "X-Request-Id"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)

    protected = APIRouter(
        dependencies=[Depends(require_auth), Depends(enforce_rate_limit)]
    )

    protected_routers = [
        config_validate.router,
        analytics.router,
        conversations.router,
        messages.router,
        prelab.router,
    ]
    for router in protected_routers:
        protected.include_router(router)

    app.include_router(protected)

    return app


app = create_app()