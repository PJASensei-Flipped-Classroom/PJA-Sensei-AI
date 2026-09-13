"""Pre-lab quiz routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_container
from app.api.schemas.requests import PreLabSubmitRequest
from app.application.container import AppContainer
from app.domain.exceptions import UnknownConversation

router = APIRouter(tags=["prelab"])


@router.get("/conversations/{conversation_id}/prelab")
async def get_prelab(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
):
    return container.prelab.get_prelab_public(conversation_id)


@router.post("/conversations/{conversation_id}/prelab")
async def submit_prelab(
    conversation_id: str,
    payload: PreLabSubmitRequest,
    container: AppContainer = Depends(get_container),
):
    return container.prelab.submit_prelab(conversation_id, payload)


@router.post(
    "/conversations/{conversation_id}/prelab/generate",
    tags=["experimental"],
)
async def generate_prelab(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
):
    try:
        return await container.prelab.generate_prelab(conversation_id)
    except UnknownConversation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
