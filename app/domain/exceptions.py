"""Domain exceptions representing business rule violations."""

from __future__ import annotations


class DomainError(Exception):
    """Bazowa klasa dla wszystkich wyjątków reguł biznesowych domeny."""

    def __init__(self, message: str = "Wystąpił błąd domenowy.") -> None:
        self.message = message
        super().__init__(message)


class UnknownConversation(DomainError):
    """Zgłaszany, gdy sesja konwersacji nie istnieje w repozytorium lub wygasła."""

    def __init__(self, conversation_id: str) -> None:
        self.conversation_id = conversation_id
        super().__init__(f"Konwersacja o identyfikatorze '{conversation_id}' nie została znaleziona.")


class PrelabRequired(DomainError):
    """Zgłaszany przy próbie interakcji bez uprzedniego zaliczenia quizu wstępnego."""

    def __init__(
        self,
        message: str = "Wymagane jest zaliczenie testu pre-lab.",
        *,
        language: str = "pl",
    ) -> None:
        self.language = "en" if language == "en" else "pl"
        super().__init__(message)


class TokenBudgetExceeded(DomainError):
    """Zgłaszany, gdy student wyczerpie limit tokenów przyznany na daną sesję."""

    def __init__(
        self,
        message: str = "Wyczerpano budżet tokenów dla bieżącej sesji.",
        *,
        language: str = "pl",
    ) -> None:
        self.language = "en" if language == "en" else "pl"
        super().__init__(message)


class RevealNotAllowed(DomainError):
    """Zgłaszany przy nieuprawnionej próbie odsłonięcia mocniejszej wskazówki."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)