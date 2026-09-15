"""Zależności FastAPI, mechanizmy Rate Limitingu oraz strażnicy przepływu wiadomości."""

from __future__ import annotations

from typing import Annotated

from fastapi import BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse

from app.api.guards import (
    ensure_prompt_safe,
    missing_file_context_response,
    require_conversation,
    requires_file_context,
)
from app.api.schemas.requests import MessageRequest
from app.application.container import AppContainer
from app.core.metrics import metrics
from app.core.rate_limit import enforce_rate_limit as enforce_rate_limit_core
from app.domain.conversation import Conversation
from app.domain.exceptions import TokenBudgetExceeded


def get_container(request: Request) -> AppContainer:
    """Pobiera kontener IoC/DI zainicjalizowany w stanie aplikacji (app.state)."""
    return request.app.state.container


def enforce_rate_limit(request: Request) -> None:
    """Weryfikuje limity wywołań API (Rate Limiting) per adres IP oraz sesję konwersacji."""
    conversation_id = request.path_params.get("conversation_id")
    enforce_rate_limit_core(request, conversation_id)


async def validate_message_request(
    conversation_id: str,
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    container: Annotated[AppContainer, Depends(get_container)],
) -> tuple[Conversation, JSONResponse | None]:
    """Przeprowadza kaskadową walidację wstępną wiadomości (pre-lab, budżet tokenów, reguły kontekstu i bezpieczeństwo)."""
    metrics.inc("requests_total")
    conversation = require_conversation(container, conversation_id)
    language = conversation.config.language

    # Weryfikacja zaliczenia quizu wstępnego oraz limitu tokenów
    try:
        container.sessions.ensure_prelab_passed(conversation)
        container.sessions.ensure_token_budget(conversation)
    except TokenBudgetExceeded:
        if not conversation.summary_generated:
            conversation.summary_generated = True
            background_tasks.add_task(
                container.summary.generate_summary,
                conversation_id,
            )
        raise

    # Sprawdzenie wymagania załączenia pliku/kodu
    if requires_file_context(conversation, request):
        payload = missing_file_context_response(language).model_dump()
        payload["message_id"] = "rejected"
        return conversation, JSONResponse(content=payload)

    # Sprawdzenie zabezpieczeń prompt injection / jailbreak
    blocked_response = await ensure_prompt_safe(
        container.security,
        request.question,
        language,
    )
    if blocked_response is not None:
        payload = blocked_response.model_dump()
        payload["message_id"] = "blocked"
        return conversation, JSONResponse(content=payload)

    return conversation, None