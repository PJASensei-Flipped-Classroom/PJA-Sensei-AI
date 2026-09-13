"""Map domain exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    PrelabRequired,
    RevealNotAllowed,
    TokenBudgetExceeded,
    UnknownConversation,
)


def blocked_payload(language: str, kind: str) -> dict:
    if kind == "prelab":
        answer = (
            "Complete the pre-lab quiz before chatting about the assignment."
            if language == "en"
            else "Ukończ quiz pre-lab, zanim zaczniesz czat o zadaniu."
        )
        feedback = "Pre-lab not passed." if language == "en" else "Pre-lab niezaliczony."
        message_id = "prelab_required"
    else:
        answer = (
            "Token budget for this session has been exhausted."
            if language == "en"
            else "Budżet tokenów dla tej sesji został wyczerpany."
        )
        feedback = "maxTokensPerSession exceeded"
        message_id = "token_budget_exceeded"
    return {
        "message_id": message_id,
        "answer": answer,
        "prompt_score": 1,
        "prompt_feedback": feedback,
        "tokens_used": 0,
        "penalty_applied": False,
        "sources": [],
        "suggested_next_step": None,
        "goal_progress": [],
    }


def _language_from_request(request: Request) -> str:
    container = getattr(request.app.state, "container", None)
    conv_id = request.path_params.get("conversation_id")
    if container and conv_id:
        conv = container.conversations.get(conv_id)
        if conv is not None:
            return conv.config.language
    return "pl"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnknownConversation)
    async def _unknown_conversation(_request: Request, _exc: UnknownConversation):
        return JSONResponse(
            status_code=404, content={"detail": "Conversation not found"}
        )

    @app.exception_handler(PrelabRequired)
    async def _prelab_required(request: Request, _exc: PrelabRequired):
        return JSONResponse(
            status_code=403,
            content=blocked_payload(_language_from_request(request), "prelab"),
        )

    @app.exception_handler(TokenBudgetExceeded)
    async def _token_budget(request: Request, _exc: TokenBudgetExceeded):
        return JSONResponse(
            status_code=403,
            content=blocked_payload(_language_from_request(request), "budget"),
        )

    @app.exception_handler(RevealNotAllowed)
    async def _reveal_not_allowed(_request: Request, exc: RevealNotAllowed):
        return JSONResponse(status_code=403, content={"detail": exc.detail})
