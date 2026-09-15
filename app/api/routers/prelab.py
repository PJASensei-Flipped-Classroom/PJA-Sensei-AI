"""Trasy obsługi quizu wstępnego (pre-lab quiz) przed dopuszczeniem do konwersacji."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.api.schemas.requests import PreLabSubmitRequest
from app.application.container import AppContainer

router = APIRouter(tags=["prelab"])


# --- Schematy DTO odpowiedzi ---

class PreLabQuestionDTO(BaseModel):
    """Pojedyncze pytanie quizowe z perspektywy studenta (bez poprawnych odpowiedzi)."""

    id: str = Field(..., description="Unikalny identyfikator pytania")
    question: str = Field(..., description="Treść pytania")
    options: list[str] = Field(default_factory=list, description="Lista wariantów do wyboru w pytaniach zamkniętych")


class PreLabPublicResponse(BaseModel):
    """Stan modułu pre-lab oraz zestaw pytań udostępniany interfejsowi studenta."""

    enabled: bool = Field(..., description="Czy pre-lab jest aktywny w bieżącej sesji")
    passed: bool = Field(..., description="Czy student zaliczył już quiz")
    questions: list[PreLabQuestionDTO] = Field(default_factory=list, description="Lista pytań quizowych")


class PreLabSubmitResponse(BaseModel):
    """Szczegółowy wynik weryfikacji nadesłanych odpowiedzi quizu wstępnego."""

    passed: bool = Field(..., description="Czy nadesłane odpowiedzi spełniły próg zaliczenia")
    score: float = Field(..., description="Uzyskany wynik punktowy lub procentowy")
    unlocked: bool = Field(default=False, description="Czy główny czat został odblokowany do dyskusji")
    feedback: str | None = Field(default=None, description="Ogólna informacja zwrotna dla studenta")
    detail: str | None = Field(default=None, description="Dodatkowe wyjaśnienia lub opis błędu")
    failed_ids: list[str] = Field(default_factory=list, description="Lista identyfikatorów pytań, na które odpowiedziano błędnie")
    attempts: int | None = Field(default=None, description="Bieżąca liczba wykorzystanych podejść")
    max_attempts: int | None = Field(default=None, description="Maksymalna dopuszczalna liczba podejść")
    hint_after_fail: str | None = Field(default=None, description="Podpowiedź dydaktyczna wyświetlana po nieudanym podejściu")


# --- Trasy i kontrolery ---

@router.get(
    "/conversations/{conversation_id}/prelab",
    response_model=PreLabPublicResponse,
    summary="Pobranie pytań quizu wstępnego (widok studenta)",
)
async def get_prelab(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> PreLabPublicResponse:
    """Zwraca stan pre-labu i pytania bez pól wrażliwych (kluczy odpowiedzi i oczekiwanych słów kluczowych)."""
    return container.prelab.get_prelab_public(conversation_id)


@router.post(
    "/conversations/{conversation_id}/prelab",
    response_model=PreLabSubmitResponse,
    summary="Przesłanie odpowiedzi do weryfikacji quizu wstępnego",
)
async def submit_prelab(
    conversation_id: str,
    payload: PreLabSubmitRequest,
    container: AppContainer = Depends(get_container),
) -> PreLabSubmitResponse:
    """Ocenia nadesłane odpowiedzi, zlicza próby i odblokowuje dostęp do asystenta po zaliczeniu."""
    return container.prelab.submit_prelab(conversation_id, payload)