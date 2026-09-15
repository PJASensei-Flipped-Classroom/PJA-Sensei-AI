"""Trasy operacyjne (ops): sondy liveness/readiness, metryki oraz frontend testera."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse

from app.api.deps import get_container
from app.application.container import AppContainer
from app.core.config import llm_is_configured
from app.core.metrics import metrics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ops"])

STATIC_DIR = Path(__file__).resolve().parents[3] / "static"
INDEX_HTML = STATIC_DIR / "index.html"
SCENARIOS_HTML = STATIC_DIR / "scenarios.html"


def _get_live_system_metrics(container: AppContainer) -> dict[str, int]:
    """Wyciąga bieżący stan liczby aktywnych sesji oraz rozmiar pamięci podręcznej."""
    return {
        "conversations": container.sessions.conversation_count(),
        "cache_size": container.cache.size,
    }


@router.get("/", summary="Podgląd interfejsu testowego")
async def serve_tester() -> FileResponse:
    """Serwuje static/index.html jako lokalny interfejs graficzny do testowania API."""
    if not INDEX_HTML.is_file():
        logger.error("Plik interfejsu testerskiego nie istnieje: %s", INDEX_HTML)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tester UI file not found. Ensure static files are built and copied into image.",
        )
    return FileResponse(INDEX_HTML)


@router.get("/scenarios", summary="Runner scenariuszy narracyjnych")
async def serve_scenarios_ui() -> FileResponse:
    """Osobne okno: karty S1–S9 z logiem każdej odpowiedzi API."""
    if not SCENARIOS_HTML.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenarios UI file not found.",
        )
    return FileResponse(SCENARIOS_HTML)


@router.get("/healthz", summary="Sonda Liveness (Kubernetes/Orchestrator)")
async def liveness() -> dict[str, str]:
    """Weryfikuje, czy proces aplikacji działa i pętla zdarzeń odpowiada na zapytania."""
    return {"status": "ok"}


@router.get("/health", summary="Sonda Readiness / Stan komponentów")
async def readiness(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    """Weryfikuje gotowość komponentów krytycznych (ChromaDB, konfiguracja LLM) do obsługi ruchu."""
    chroma_ready = container.rag.chroma_ok()
    llm_ready = llm_is_configured()
    is_healthy = chroma_ready and llm_ready

    payload = {
        "status": "ok" if is_healthy else "degraded",
        "llm_configured": llm_ready,
        "chroma_ok": chroma_ready,
        **_get_live_system_metrics(container),
    }

    if not is_healthy:
        # Kod 503 informuje ingress/load-balancer o konieczności odcięcia ruchu od tej instancji
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=payload,
        )

    return payload


@router.get("/metrics", summary="Zrzut metryk JSON")
async def get_metrics(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    """Zwraca migawkę liczników aplikacji wzbogaconą o bieżący stan sesji i cache w formacie JSON."""
    return {
        **metrics.snapshot(),
        **_get_live_system_metrics(container),
    }


@router.get(
    "/metrics/prometheus",
    response_class=PlainTextResponse,
    summary="Metryki w formacie Prometheus",
)
async def get_metrics_prometheus(
    container: AppContainer = Depends(get_container),
) -> PlainTextResponse:
    """Eksportuje metryki w standardowym formacie tekstowym Prometheus exposition format."""
    extra_metrics = _get_live_system_metrics(container)
    return PlainTextResponse(
        content=metrics.prometheus_text(extra_metrics),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )