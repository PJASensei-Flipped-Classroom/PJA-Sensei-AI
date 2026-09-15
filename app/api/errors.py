"""Translacja wyjątków domenowych aplikacji na ustrukturyzowane odpowiedzi HTTP."""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    PrelabRequired,
    RevealNotAllowed,
    TokenBudgetExceeded,
    UnknownConversation,
)


class BlockReason(str, Enum):
    """Powody wczesnego zablokowania czatu mapowane na kontrakt MessageResponse."""

    PRELAB = "prelab"
    TOKEN_BUDGET = "token_budget"


_MESSAGES_CONFIG: dict[BlockReason, dict[str, dict[str, str]]] = {
    BlockReason.PRELAB: {
        "en": {
            "message_id": "prelab_required",
            "answer": "Complete the pre-lab quiz before chatting about the assignment.",
            "feedback": "Pre-lab not passed.",
        },
        "pl": {
            "message_id": "prelab_required",
            "answer": "Ukończ quiz pre-lab, zanim zaczniesz czat o zadaniu.",
            "feedback": "Pre-lab niezaliczony.",
        },
    },
    BlockReason.TOKEN_BUDGET: {
        "en": {
            "message_id": "token_budget_exceeded",
            "answer": "Token budget for this session has been exhausted.",
            "feedback": "maxTokensPerSession exceeded",
        },
        "pl": {
            "message_id": "token_budget_exceeded",
            "answer": "Budżet tokenów dla tej sesji został wyczerpany.",
            "feedback": "maxTokensPerSession exceeded",
        },
    },
}


def build_blocked_payload(language: str, reason: BlockReason) -> dict[str, Any]:
    """Generuje ustrukturyzowany słownik blokady, w pełni zgodny ze schematem MessageResponse."""
    lang_key = "en" if language == "en" else "pl"
    text_data = _MESSAGES_CONFIG[reason][lang_key]

    return {
        "message_id": text_data["message_id"],
        "answer": text_data["answer"],
        "prompt_score": 1,
        "prompt_feedback": text_data["feedback"],
        "tokens_used": 0,
        "penalty_applied": False,
        "sources": [],
        "suggested_next_step": None,
        "goal_progress": [],
        "next_checkpoint": None,
    }


def _resolve_language(request: Request, exc: object | None = None) -> str:
    """Język z wyjątku sesji, potem request.state, na końcu Accept-Language / pl."""
    lang = getattr(exc, "language", None)
    if lang in ("en", "pl"):
        return lang

    state_lang = getattr(request.state, "language", None)
    if state_lang in ("en", "pl"):
        return state_lang

    accept_lang = request.headers.get("Accept-Language", "").lower()
    if accept_lang.startswith("en"):
        return "en"
    return "pl"


def register_exception_handlers(app: FastAPI) -> None:
    """Rejestruje globalne procedury przechwytywania wyjątków domenowych w instancji FastAPI."""

    @app.exception_handler(UnknownConversation)
    async def _handle_unknown_conversation(_request: Request, _exc: UnknownConversation) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Conversation not found"},
        )

    @app.exception_handler(PrelabRequired)
    async def _handle_prelab_required(request: Request, exc: PrelabRequired) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=build_blocked_payload(_resolve_language(request, exc), BlockReason.PRELAB),
        )

    @app.exception_handler(TokenBudgetExceeded)
    async def _handle_token_budget(request: Request, exc: TokenBudgetExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=build_blocked_payload(_resolve_language(request, exc), BlockReason.TOKEN_BUDGET),
        )

    @app.exception_handler(RevealNotAllowed)
    async def _handle_reveal_not_allowed(_request: Request, exc: RevealNotAllowed) -> JSONResponse:
        detail_msg = getattr(exc, "detail", "Hint reveal not allowed")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": detail_msg},
        )