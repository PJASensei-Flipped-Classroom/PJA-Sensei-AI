"""Application-layer request DTOs (no dependency on app.api)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.sensei import CodeContext, SenseiConfig


class PreLabAnswerItem(BaseModel):
    """Jedna odpowiedź studenta na pytanie quizu pre-lab."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Identyfikator pytania quizowego")
    answer: str = Field(..., min_length=1, description="Odpowiedź zaznaczona/wpisana przez studenta")


class PreLabSubmitRequest(BaseModel):
    """Payload POST /prelab — lista odpowiedzi do ewaluacji."""

    model_config = ConfigDict(frozen=True)

    answers: list[PreLabAnswerItem] = Field(..., min_length=1, description="Komplet odpowiedzi do quizu")


class MessageRequest(BaseModel):
    """Payload wiadomości czatu: pytanie, kontekst edytora, opcjonalny klucz idempotencji."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(..., min_length=1, description="Pytanie zadane asystentowi")
    code_context: CodeContext = Field(..., description="Stan edytora kodu w momencie wysłania pytania")
    client_message_id: str | None = Field(default=None, description="Klucz idempotencji żądania")


class IdeEventRequest(BaseModel):
    """Zdarzenie telemetryczne z rozszerzenia IDE (copy/paste/file)."""

    model_config = ConfigDict(frozen=True)

    type: Literal["copy_blocked", "file_opened", "paste_attempt"] = Field(
        ..., description="Kategoria zdarzenia telemetrycznego z edytora"
    )
    meta: dict[str, Any] = Field(default_factory=dict, description="Dodatkowy kontekst zdarzenia")


class RevealHintRequest(BaseModel):
    """Żądanie mocniejszej podpowiedzi (reveal) po spełnieniu bramki frustracji."""

    model_config = ConfigDict(frozen=True)

    code_context: CodeContext | None = Field(default=None, description="Opcjonalny zrzut kodu przy prośbie o podpowiedź")
    focus: str | None = Field(default=None, description="Obszar problemu wskazany przez studenta")


class FeedbackRequest(BaseModel):
    """Ocena jakości odpowiedzi asystenta przez studenta."""

    model_config = ConfigDict(frozen=True)

    rating: int = Field(..., ge=1, le=5, description="Ocena trafności wskazówki w skali 1-5")
    comment: str | None = Field(default=None, max_length=1000, description="Opcjonalny komentarz zwrotny studenta")


class StartRequest(BaseModel):
    """Payload startu sesji: treść zadania + SenseiConfig."""

    model_config = ConfigDict(frozen=True)

    problem_description: str = Field(..., min_length=1, description="Treść zadania laboratoryjnego")
    config: SenseiConfig = Field(..., description="Konfiguracja ograniczeń i zachowania asystenta")


class ValidateConfigRequest(BaseModel):
    """Surowy słownik konfiguracji do /validate-config (bez wymuszenia SenseiConfig)."""

    model_config = ConfigDict(frozen=True)

    config: dict[str, Any] = Field(..., description="Surowy słownik konfiguracji do walidacji ze schematem")