"""Cross-session analytics."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.application.container import AppContainer

router = APIRouter(tags=["analytics", "experimental"])


@router.get("/analytics/correlations")
async def analytics_correlations(
    container: AppContainer = Depends(get_container),
):
    return container.analytics.build_correlations()
