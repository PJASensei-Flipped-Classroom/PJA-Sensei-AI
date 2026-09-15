"""Niezmienne obiekty transferu danych (DTO) warstwy aplikacji (brak zależności od app.api)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.sensei import CodeContext, SenseiConfig


class _ImmutableDTO(BaseModel):
    """Baza dla niemodyfikowalnych obiektów transferu danych (ochrona przed mutacjami)."""

    model_config = ConfigDict(frozen=True)


class PreLabAnswerItem(_ImmutableDTO):
    """Pojedyncza odpowiedź studenta nadesłana na pytanie quizu wstępnego."""

    id: str = Field(..., min_length=1, description="Identyfikator pytania quizowego")
    answer: str = Field(..., min_length=1, description="Odpowiedź zaznaczona lub wpisana przez studenta")


class PreLabSubmitRequest(_ImmutableDTO):
    """Ciało żądania POST /prelab zawierające zestaw odpowiedzi do ewaluacji."""

    answers: list[PreLabAnswerItem] = Field(
        ...,
        min_length=1,
        description="Lista nadesłanych odpowiedzi (wymagany co najmniej jeden element)",
    )


class MessageRequest(_ImmutableDTO):
    """Ciało żądania wysyłki wiadomości do czatu asystenta."""

    question: str = Field(..., min_length=1, description="Treść pytania zadanego przez studenta")
    code_context: CodeContext = Field(..., description="Stan edytora kodu w momencie zadawania pytania")
    client_message_id: str | None = Field(
        default=None,
        description="Opcjonalny unikalny klucz idempotencji nadany po stronie klienta",
    )


class IdeEventRequest(_ImmutableDTO):
    """Zdarzenie telemetryczne zarejestrowane przez wtyczkę środowiska IDE."""

    type: Literal["copy_blocked", "file_opened", "paste_attempt"] = Field(
        ...,
        description="Typ zdarzenia z edytora: zablokowanie kopiowania, otwarcie pliku lub próba wklejenia",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Dodatkowy kontekst zdarzenia (np. nazwa pliku, długość wklejanego tekstu)",
    )


class RevealHintRequest(_ImmutableDTO):
    """Żądanie odsłonięcia mocniejszej podpowiedzi (reveal) przy sustained frustration."""

    code_context: CodeContext | None = Field(
        default=None,
        description="Bieżący stan kodu przesłany wraz z prośbą o wskazówkę",
    )
    focus: str | None = Field(
        default=None,
        description="Opcjonalne zawężenie tematyczne wskazane przez studenta",
    )


class FeedbackRequest(_ImmutableDTO):
    """Ocena jakości dydaktycznej konkretnej odpowiedzi asystenta."""

    rating: int = Field(..., ge=1, le=5, description="Ocena w skali Likerta od 1 (bezużyteczna) do 5 (bardzo pomocna)")
    comment: str | None = Field(
        default=None,
        max_length=1000,
        description="Opcjonalny komentarz tekstowy studenta (maksymalnie 1000 znaków)",
    )


class StartRequest(_ImmutableDTO):
    """Ciało żądania inicjalizacji nowej sesji laboratoryjnej."""

    problem_description: str = Field(..., min_length=1, description="Opis zadania programistycznego")
    config: SenseiConfig = Field(..., description="Zwalidowana regułami domenowymi konfiguracja laboratorium")


class ValidateConfigRequest(_ImmutableDTO):
    """Surowy słownik konfiguracji do wstępnej walidacji przedstartowej (/validate-config)."""

    config: dict[str, Any] = Field(
        ...,
        description="Niezwalidowany słownik JSON sprawdzany pod kątem poprawności składniowej i schematu",
    )