"""HTTP guards for conversation access and prompt safety."""

from __future__ import annotations

from fastapi import HTTPException

from app.adapters.security import SecurityService
from app.api.schemas.requests import MessageRequest
from app.api.schemas.responses import MessageResponse
from app.application.container import AppContainer
from app.domain.conversation import Conversation
from app.domain.exceptions import UnknownConversation


def require_conversation(
    container: AppContainer, conversation_id: str
) -> Conversation:
    conversation = container.conversations.get(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )
    return conversation


def get_conversation(container: AppContainer, conversation_id: str) -> Conversation:
    """Raise domain UnknownConversation (mapped by exception handlers)."""
    conversation = container.conversations.get(conversation_id)
    if not conversation:
        raise UnknownConversation(conversation_id)
    return conversation


def missing_file_context_response(language: str) -> MessageResponse:
    return MessageResponse(
        answer=(
            "To zadanie wymaga analizy kodu. Otwórz odpowiedni plik w edytorze VS Code zanim zadasz pytanie."
            if language == "pl"
            else "This task requires code analysis. Please open the relevant file in your VS Code editor before asking."
        ),
        prompt_score=1,
        prompt_feedback=(
            "Brak przesłanego kontekstu pliku (Naruszenie ideRestrictions)."
            if language == "pl"
            else "Missing file context (ideRestrictions violation)."
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
    restrictions = conversation.config.ideRestrictions
    if not restrictions or not restrictions.requireFileContextForChat:
        return False
    return not request.code_context.current_code.strip()


async def ensure_prompt_safe(
    security_service: SecurityService,
    question: str,
    language: str,
) -> MessageResponse | None:
    is_safe = await security_service.is_prompt_safe(question)
    if is_safe:
        return None
    blocked = security_service.get_blocked_response(language)
    return MessageResponse(**blocked)
