"""Health, readiness, metrics, and tester UI routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse

from app.api.deps import get_container
from app.application.container import AppContainer
from app.core.config import openrouter_key_is_configured
from app.core.metrics import metrics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ops"])

STATIC_DIR = Path(__file__).resolve().parents[3] / "static"
INDEX_HTML = STATIC_DIR / "index.html"


@router.get("/", summary="Podgląd interfejsu testowego")
async def serve_tester() -> FileResponse:
    """Serwuje static/index.html — lokalny tester manualny API."""
    if not INDEX_HTML.is_file():
        logger.error("Plik interfejsu testerskiego nie istnieje pod ścieżką: %s", INDEX_HTML)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tester UI file not found. Ensure static files are built and copied into image.",
        )
    return FileResponse(INDEX_HTML)


@router.get("/healthz", summary="Sonda Liveness (Kubernetes/Orchestrator)")
async def liveness() -> dict[str, str]:
    """Tylko sprawdzenie, czy pętla zdarzeń procesu żyje."""
    return {"status": "ok"}


@router.get("/health", summary="Sonda Readiness / Stan komponentów")
async def readiness(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    """Weryfikacja gotowości serwisu do przyjmowania ruchu."""
    chroma_ready = container.rag.chroma_ok()
    has_api_key = openrouter_key_is_configured()

    system_healthy = chroma_ready and has_api_key

    response_payload = {
        "status": "ok" if system_healthy else "degraded",
        "openrouter_key_configured": has_api_key,
        "conversations": container.sessions.conversation_count(),
        "cache_size": container.cache.size,
        "chroma_ok": chroma_ready,
    }

    if not system_healthy:
        # Zwracamy HTTP 503, aby load balancer tymczasowo odciął ruch od tego poda
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response_payload,
        )

    return response_payload


@router.get("/metrics", summary="Zrzut metryk JSON")
async def get_metrics(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    """Zwraca snapshot liczników procesu + rozmiar cache/sesji."""
    snap = metrics.snapshot()
    snap.update(
        {
            "conversations": container.sessions.conversation_count(),
            "cache_size": container.cache.size,
        }
    )
    return snap


@router.get(
    "/metrics/prometheus",
    response_class=PlainTextResponse,
    summary="Metryki w formacie Prometheus",
)
async def get_metrics_prometheus(
    container: AppContainer = Depends(get_container),
) -> PlainTextResponse:
    """Ekspozycja metryk w formacie text/plain Prometheus exposition."""
    extra = {
        "conversations": container.sessions.conversation_count(),
        "cache_size": container.cache.size,
    }
    return PlainTextResponse(
        metrics.prometheus_text(extra),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )