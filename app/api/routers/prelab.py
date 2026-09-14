"""Pre-lab quiz routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.api.schemas.requests import PreLabSubmitRequest
from app.application.container import AppContainer

router = APIRouter(tags=["prelab"])


# --- Schematy DTO odpowiedzi ---

class PreLabQuestionDTO(BaseModel):
    """Publiczna treść pytania quizowego (bez expected_keywords)."""

    id: str
    question: str
    options: list[str] = Field(default_factory=list)


class PreLabPublicResponse(BaseModel):
    """Stan prelab widoczny dla studenta przed/po zaliczeniu."""

    enabled: bool
    passed: bool
    questions: list[PreLabQuestionDTO] = Field(default_factory=list)


class PreLabSubmitResponse(BaseModel):
    """Wynik oceny odpowiedzi quizu wstępnego."""

    passed: bool
    score: float
    feedback: str | None = None
    detail: str | None = None
    unlocked: bool = False
    failed_ids: list[str] = Field(default_factory=list)
    attempts: int | None = None
    max_attempts: int | None = None
    hint_after_fail: str | None = None


# --- Trasy ---

@router.get(
    "/conversations/{conversation_id}/prelab",
    response_model=PreLabPublicResponse,
    summary="Pobranie pytań quizu wstępnego (widok studenta)",
)
async def get_prelab(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> Any:
    """Zwraca pytania bez klucza odpowiedzi; enabled=false gdy prelab wyłączony."""
    return container.prelab.get_prelab_public(conversation_id)


@router.post(
    "/conversations/{conversation_id}/prelab",
    response_model=PreLabSubmitResponse,
    status_code=status.HTTP_200_OK,
    summary="Przesłanie odpowiedzi do weryfikacji quizu wstępnego",
)
async def submit_prelab(
    conversation_id: str,
    payload: PreLabSubmitRequest,
    container: AppContainer = Depends(get_container),
) -> Any:
    """Ocenia odpowiedzi i odblokowuje czat przy zaliczeniu / wyczerpaniu prób."""
    return container.prelab.submit_prelab(conversation_id, payload)