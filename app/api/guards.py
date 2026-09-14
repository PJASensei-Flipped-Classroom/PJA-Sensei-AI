"""HTTP guards for conversation access and prompt safety."""

from __future__ import annotations

from app.api.schemas.requests import MessageRequest
from app.api.schemas.responses import MessageResponse
from app.application.container import AppContainer
from app.domain.conversation import Conversation
from app.ports import SecurityPort


def require_conversation(
    container: AppContainer, conversation_id: str
) -> Conversation:
    """Zwraca aktywną konwersację lub rzuca wyjątek domenowy UnknownConversation (404)."""
    return container.sessions.get_conversation_or_404(conversation_id)


def missing_file_context_response(language: str = "pl") -> MessageResponse:
    """Generuje ustrukturyzowaną odmowę w przypadku braku otwartego pliku w edytorze."""
    is_pl = language == "pl"
    return MessageResponse(
        answer=(
            "To zadanie wymaga analizy kodu. Otwórz odpowiedni plik w edytorze VS Code zanim zadasz pytanie."
            if is_pl
            else "This task requires code analysis. Please open the relevant file in your VS Code editor before asking."
        ),
        prompt_score=1,
        prompt_feedback=(
            "Brak przesłanego kontekstu pliku (Naruszenie zasad laboratorium)."
            if is_pl
            else "Missing file context (Editor restrictions violation)."
        ),
        tokens_used=0,
        penalty_applied=False,
        sources=[],
        suggested_next_step=None,
        goal_progress=[],
    )


def requires_file_context(
    conversation: Conversation, request: MessageRequest
) -> bool:
    """Sprawdza, czy konfiguracja wymusza obecność kodu i czy student go dostarczył."""
    # Tryb theory: pytania koncepcyjne bez edytora — nie wymuszaj pliku.
    agent = getattr(conversation.config, "agent_behavior", None) or getattr(
        conversation.config, "agentBehavior", None
    )
    mode = getattr(agent, "mode", None) if agent else None
    if mode == "theory":
        return False

    restrictions = getattr(conversation.config, "ide_restrictions", None) or getattr(
        conversation.config, "ideRestrictions", None
    )
    if not restrictions:
        return False

    is_required = getattr(restrictions, "require_file_context_for_chat", None) or getattr(
        restrictions, "requireFileContextForChat", False
    )
    if not is_required:
        return False

    # Defensywne sprawdzenie obecności kodu (ochrona przed None)
    code_ctx = getattr(request, "code_context", None)
    current_code = getattr(code_ctx, "current_code", None) if code_ctx else None

    return not current_code or not current_code.strip()


async def ensure_prompt_safe(
    security_service: SecurityPort,
    question: str,
    language: str = "pl",
) -> MessageResponse | None:
    """Weryfikuje prompt przez interfejs SecurityPort i zwraca gotową odpowiedź blokującą lub None."""
    is_safe = await security_service.is_prompt_safe(question)
    if is_safe:
        return None

    blocked = security_service.injection_blocked_response(language)
    return MessageResponse(**blocked)