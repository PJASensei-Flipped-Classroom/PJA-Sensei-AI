"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import BackgroundTasks, Request
from fastapi.responses import JSONResponse

from app.api.errors import blocked_payload
from app.api.guards import (
    ensure_prompt_safe,
    missing_file_context_response,
    require_conversation,
    requires_file_context,
)
from app.api.schemas.requests import MessageRequest
from app.application.container import AppContainer
from app.core.metrics import metrics
from app.core.rate_limit import client_key, rate_limiter
from app.domain.exceptions import PrelabRequired, TokenBudgetExceeded

_container: AppContainer | None = None


def init_container(container: AppContainer | None = None) -> AppContainer:
    global _container
    _container = container or AppContainer()
    return _container


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


def enforce_rate_limit(request: Request) -> None:
    conv_id = request.path_params.get("conversation_id")
    rate_limiter.check(client_key(request, conv_id))


async def validate_message_request(
    conversation_id: str,
    request: MessageRequest,
    http_request: Request,
    background_tasks: BackgroundTasks | None = None,
    container: AppContainer | None = None,
) -> tuple[object, JSONResponse | None]:
    container = container or get_container()
    metrics.inc("requests_total")
    conversation = require_conversation(container, conversation_id)
    language = conversation.config.language

    try:
        container.sessions.ensure_prelab_passed(conversation)
        container.sessions.ensure_token_budget(conversation)
    except PrelabRequired:
        return conversation, JSONResponse(
            blocked_payload(language, "prelab"), status_code=403
        )
    except TokenBudgetExceeded:
        if background_tasks is not None and not conversation.summary_generated:
            conversation.summary_generated = True
            background_tasks.add_task(
                container.summary.generate_summary, conversation_id
            )
        return conversation, JSONResponse(
            blocked_payload(language, "budget"), status_code=403
        )

    if requires_file_context(conversation, request):
        payload = missing_file_context_response(language).model_dump()
        payload["message_id"] = "rejected"
        return conversation, JSONResponse(payload)

    blocked = await ensure_prompt_safe(
        container.security, request.question, language
    )
    if blocked:
        payload = blocked.model_dump()
        payload["message_id"] = "blocked"
        return conversation, JSONResponse(payload)

    return conversation, None
