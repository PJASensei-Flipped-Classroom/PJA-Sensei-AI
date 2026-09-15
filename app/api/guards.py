"""Strażnicy (guards) warstwy HTTP: weryfikacja dostępu do sesji, kontekstu pliku oraz bezpieczeństwa promptu."""

from __future__ import annotations

from typing import Any

from app.api.schemas.requests import MessageRequest
from app.api.schemas.responses import MessageResponse
from app.application.container import AppContainer
from app.domain.conversation import Conversation
from app.ports import SecurityPort

# Tabela komunikatów odmowy przy braku załączonego kodu źródłowego
_MISSING_FILE_MESSAGES: dict[str, dict[str, str]] = {
    "pl": {
        "answer": (
            "To zadanie wymaga analizy kodu. Otwórz odpowiedni plik "
            "w edytorze VS Code zanim zadasz pytanie."
        ),
        "feedback": "Brak przesłanego kontekstu pliku (Naruszenie zasad laboratorium).",
    },
    "en": {
        "answer": (
            "This task requires code analysis. Please open the relevant file "
            "in your VS Code editor before asking."
        ),
        "feedback": "Missing file context (Editor restrictions violation).",
    },
}


def _get_flexible_attr(target: Any, *candidates: str, default: Any = None) -> Any:
    """Pobiera pierwszy istniejący atrybut spośród podanych nazw (obsługa camelCase vs snake_case)."""
    if target is None:
        return default
    for attr in candidates:
        if (val := getattr(target, attr, None)) is not None:
            return val
    return default


def require_conversation(
    container: AppContainer,
    conversation_id: str,
) -> Conversation:
    """Zwraca aktywną konwersację lub rzuca wyjątek domenowy UnknownConversation (mapowany na 404)."""
    return container.sessions.get_conversation_or_404(conversation_id)


def missing_file_context_response(language: str = "pl") -> MessageResponse:
    """Generuje ustrukturyzowany model odpowiedzi blokującej przy braku załączonego pliku."""
    lang_key = "pl" if language == "pl" else "en"
    texts = _MISSING_FILE_MESSAGES[lang_key]

    return MessageResponse(
        answer=texts["answer"],
        prompt_score=1,
        prompt_feedback=texts["feedback"],
        tokens_used=0,
        penalty_applied=False,
        sources=[],
        suggested_next_step=None,
        goal_progress=[],
    )


def requires_file_context(
    conversation: Conversation,
    request: MessageRequest,
) -> bool:
    """Weryfikuje, czy konfiguracja wymusza obecność kodu i czy student go nie dostarczył."""
    cfg = conversation.config

    # W trybie teoretycznym ('theory') obecność pliku nigdy nie jest wymagana
    agent = _get_flexible_attr(cfg, "agent_behavior", "agentBehavior")
    if getattr(agent, "mode", None) == "theory":
        return False

    restrictions = _get_flexible_attr(cfg, "ide_restrictions", "ideRestrictions")
    if not restrictions:
        return False

    is_enforced = _get_flexible_attr(
        restrictions,
        "require_file_context_for_chat",
        "requireFileContextForChat",
        default=False,
    )
    if not is_enforced:
        return False

    # Sprawdzenie obecności nietrywialnego kodu źródłowego
    code_ctx = getattr(request, "code_context", None)
    current_code = getattr(code_ctx, "current_code", None) if code_ctx else None

    # Zwraca True, jeśli wymóg istnieje, ale kodu brak lub składa się wyłącznie z białych znaków
    return not (current_code and current_code.strip())


async def ensure_prompt_safe(
    security_service: SecurityPort,
    question: str,
    language: str = "pl",
) -> MessageResponse | None:
    """Weryfikuje prompt przez SecurityPort i zwraca gotową odpowiedź blokującą lub None."""
    if await security_service.is_prompt_safe(question):
        return None

    blocked_data = security_service.injection_blocked_response(language)
    return MessageResponse(**blocked_data)