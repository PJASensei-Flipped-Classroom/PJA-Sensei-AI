"""Modele odpowiedzi HTTP (DTO) dla interfejsu czatu i telemetrii dydaktycznej."""

from __future__ import annotations

from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DebugInfo(BaseModel):
    """Metryki diagnostyczne dołączane do odpowiedzi czatu (poziom frustracji, oceny, diff kodu)."""

    model_config = ConfigDict(frozen=True)

    is_frustrated: bool = Field(..., description="Wskaźnik wykrycia frustracji u studenta")
    avg_score: float = Field(..., ge=0.0, le=10.0, description="Średnia ocen promptów w sesji (zakres 0.0–10.0)")
    code_changed: bool = Field(..., description="Czy kod w edytorze IDE uległ zmianie od ostatniego zapytania")


class SourceRef(BaseModel):
    """Odnośnik do materiału źródłowego wykorzystanego w odpowiedzi (RAG lub cytowanie zewnętrzne)."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1, description="Tytuł lub nagłówek materiału referencyjnego")
    url: str = Field(..., description="Bezpośredni adres URL źródła")
    timestamp: str | None = Field(default=None, description="Znacznik czasu dla nagrań wideo (np. '04:15')")
    page: int | None = Field(default=None, ge=1, description="Numer strony w dokumencie PDF (indeksowany od 1)")

    @field_validator("page", mode="before")
    @classmethod
    def _coerce_page_to_optional_int(cls, value: object) -> int | None:
        """Konwertuje puste stringi na None oraz rzutuje liczbowe stringi z metadanych ChromaDB."""
        if value in ("", None):
            return None
        try:
            return int(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None


class GoalProgressItem(BaseModel):
    """Bieżący stan realizacji pojedynczego celu dydaktycznego zdefiniowanego w konfiguracji."""

    model_config = ConfigDict(frozen=True)

    goal: str = Field(..., min_length=1, description="Opis lub nazwa celu edukacyjnego")
    status: Literal["not_started", "in_progress", "done"] = Field(
        default="not_started",
        description="Faza realizacji podzadania",
    )


class NextCheckpoint(BaseModel):
    """Wskazówka i powiązanie z kolejnym kamieniem milowym odblokowanym w sesji."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unikalny identyfikator kamienia milowego")
    hint: str | None = Field(default=None, description="Podpowiedź kierująca studenta do kolejnego etapu")
    after_goal: str | None = Field(default=None, description="Cel dydaktyczny warunkujący ten checkpoint")


class MessageResponse(BaseModel):
    """Podstawowy model odpowiedzi asystenta zwracany do klienta czatu."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unikalny identyfikator wiadomości generowany po stronie serwera",
    )
    answer: str = Field(..., min_length=1, description="Merytoryczna odpowiedź dydaktyczna asystenta")
    prompt_score: int = Field(..., ge=1, le=10, description="Ocena jakości pytania studenta w skali 1–10")
    prompt_feedback: str = Field(..., description="Komentarz uzasadniający ocenę promptu ze wskazówkami")
    tokens_used: int = Field(..., ge=0, description="Łączna liczba tokenów zużyta na przetworzenie zapytania")
    is_cached: bool = Field(default=False, description="Flaga informująca, czy odpowiedź pobrano z pamięci podręcznej")
    penalty_applied: bool = Field(default=False, description="Czy nałożono karę za próbę jailbreaku / nadużycia")
    sources: list[SourceRef] = Field(
        default_factory=list,
        description="Materiały referencyjne i cytaty dołączone do odpowiedzi",
    )
    suggested_next_step: str | None = Field(
        default=None,
        description="Sugerowany następny krok w pracy nad zadaniem",
    )
    goal_progress: list[GoalProgressItem] = Field(
        default_factory=list,
        description="Zestawienie postępów w realizacji celów laboratoryjnych",
    )
    next_checkpoint: NextCheckpoint | None = Field(
        default=None,
        description="Dane najbliższego odblokowanego punktu kontrolnego",
    )
    debug_info: DebugInfo | None = Field(
        default=None,
        description="Metryki pomocnicze dla instruktora lub badacza",
    )
    model: str | None = Field(
        default=None,
        description="Identyfikator modelu LLM użytego do generacji (None przy odpowiedzi z cache lub błędu)",
    )
    client_message_id: str | None = Field(
        default=None,
        description="Identyfikator korelacyjny przekazany opcjonalnie przez klienta IDE",
    )