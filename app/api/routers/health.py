"""Health, metrics, and tester UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, PlainTextResponse

from app.api.deps import get_container
from app.application.container import AppContainer
from app.core.config import OPENROUTER_API_KEY
from app.core.metrics import metrics

router = APIRouter(tags=["ops"])

INDEX_HTML = Path(__file__).resolve().parents[3] / "static" / "index.html"


@router.get("/")
async def serve_tester():
    return FileResponse(INDEX_HTML)


@router.get("/health")
async def health(container: AppContainer = Depends(get_container)):
    container.sessions.purge_stale_conversations()
    return {
        "status": "ok",
        "openrouter_key_configured": bool(OPENROUTER_API_KEY),
        "conversations": len(container.conversations),
        "cache_size": container.cache.size,
        "chroma_ok": container.rag.chroma_ok(),
    }


@router.get("/metrics")
async def get_metrics(
    format: str | None = None,
    container: AppContainer = Depends(get_container),
):
    extra = {
        "conversations": len(container.conversations),
        "cache_size": container.cache.size,
    }
    if format and format.lower() in ("prometheus", "prom", "text"):
        return PlainTextResponse(
            metrics.prometheus_text(extra),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    snap = metrics.snapshot()
    snap.update(extra)
    return snap


@router.get("/metrics/prometheus")
async def get_metrics_prometheus(
    container: AppContainer = Depends(get_container),
):
    return await get_metrics(format="prometheus", container=container)
