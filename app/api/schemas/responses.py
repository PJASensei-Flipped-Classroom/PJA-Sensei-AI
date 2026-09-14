"""HTTP response models."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DebugInfo(BaseModel):
    """Debugowe pola odpowiedzi czatu (frustracja, średnia ocen, zmiana kodu)."""

    model_config = ConfigDict(frozen=True)

    is_frustrated: bool = Field(..., description="Wskaźnik wykrycia frustracji u użytkownika")
    avg_score: float = Field(..., ge=0.0, le=10.0, description="Średnia ocena jakości promptów w sesji (1–10)")
    code_changed: bool = Field(..., description="Czy kod w edytorze uległ zmianie od ostatniego zapytania")


class SourceRef(BaseModel):
    """Referencja do materiału RAG cytowanego w odpowiedzi."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1, description="Tytuł materiału referencyjnego")
    url: str = Field(..., description="Adres URL źródła")
    timestamp: str | None = Field(default=None, description="Znacznik czasu dla materiałów wideo (np. 12:45)")
    page: int | None = Field(default=None, ge=1, description="Numer strony w dokumencie PDF")

    @field_validator("page", mode="before")
    @classmethod
    def _empty_page_to_none(cls, value: object) -> object:
        """Puste stringi z Chroma/metadata mapujemy na None (kontrakt OpenAPI)."""
        if value in ("", None):
            return None
        return value


class GoalProgressItem(BaseModel):
    """Element postępu względem celu dydaktycznego z konfiguracji."""

    model_config = ConfigDict(frozen=True)

    goal: str = Field(..., min_length=1, description="Opis celu dydaktycznego")
    status: Literal["not_started", "in_progress", "done"] = Field(
        default="not_started",
        description="Stan realizacji podzadania",
    )


class NextCheckpoint(BaseModel):
    """Wskazówka dotycząca kolejnego odblokowanego kamienia milowego."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unikalny identyfikator punktu kontrolnego")
    hint: str | None = Field(default=None, description="Podpowiedź naprowadzająca studenta")
    after_goal: str | None = Field(default=None, description="Cel powiązany z tym punktem kontrolnym")


class MessageResponse(BaseModel):
    """Główny model odpowiedzi asystenta w czacie."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identyfikator wiadomości wygenerowany po stronie serwera",
    )
    answer: str = Field(..., min_length=1, description="Odpowiedź dydaktyczna asystenta")
    prompt_score: int = Field(..., ge=1, le=10, description="Ocena jakości zadanego pytania w skali 1–10")
    prompt_feedback: str = Field(..., description="Uzasadnienie oceny promptu i wskazówki")
    tokens_used: int = Field(..., ge=0, description="Całkowita liczba tokenów skonsumowana przez zapytanie")
    is_cached: bool = Field(default=False, description="Czy odpowiedź pochodzi z pamięci podręcznej")
    penalty_applied: bool = Field(default=False, description="Czy nałożono karę za próbę obejścia zasad")
    sources: list[SourceRef] = Field(
        default_factory=list,
        description="Materiały źródłowe wykorzystane do odpowiedzi (RAG / cytaty)",
    )
    suggested_next_step: str | None = Field(
        default=None,
        description="Propozycja kolejnego kroku w procesie rozwiązywania zadania",
    )
    goal_progress: list[GoalProgressItem] = Field(
        default_factory=list,
        description="Aktualny stan realizacji celów laboratoryjnych",
    )
    next_checkpoint: NextCheckpoint | None = Field(
        default=None,
        description="Informacje o kolejnym kamieniu milowym",
    )
    debug_info: DebugInfo | None = Field(
        default=None,
        description="Metryki pomocnicze dla instruktora/badacza",
    )
    model: str | None = Field(
        default=None,
        description="Identyfikator modelu LLM użytego do wygenerowania odpowiedzi (None gdy brak wywołania LLM)",
    )
    client_message_id: str | None = Field(
        default=None,
        description="Opcjonalny identyfikator powiązany po stronie klienta",
    )