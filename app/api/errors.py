"""Map domain exceptions to HTTP responses."""

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
    """Powody wczesnego zablokowania czatu mapowane na spójny payload MessageResponse."""

    PRELAB = "prelab"
    TOKEN_BUDGET = "token_budget"


def build_blocked_payload(language: str, reason: BlockReason) -> dict[str, Any]:
    """Generuje spójny z MessageResponse payload błędu dla klienta czatu."""
    is_en = language == "en"

    if reason == BlockReason.PRELAB:
        answer = (
            "Complete the pre-lab quiz before chatting about the assignment."
            if is_en
            else "Ukończ quiz pre-lab, zanim zaczniesz czat o zadaniu."
        )
        feedback = "Pre-lab not passed." if is_en else "Pre-lab niezaliczony."
        message_id = "prelab_required"
    else:
        answer = (
            "Token budget for this session has been exhausted."
            if is_en
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
        "next_checkpoint": None,
    }


def _resolve_language(request: Request) -> str:
    """Bezpiecznie wyznacza język bez ponownego odpytywania serwisów domenowych."""
    # Opcja 1: Pobranie z nagłówka żądania (szybkie i odporne na błędy)
    accept_lang = request.headers.get("Accept-Language", "").lower()
    if "en" in accept_lang:
        return "en"

    # Opcja 2: Fallback na stan sesji, jeśli dostępny w request.state
    if hasattr(request.state, "language"):
        return request.state.language

    return "pl"


def register_exception_handlers(app: FastAPI) -> None:
    """Rejestruje globalne translatory wyjątków domenowych na kody HTTP."""

    @app.exception_handler(UnknownConversation)
    async def _handle_unknown_conversation(_request: Request, _exc: UnknownConversation) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Conversation not found"},
        )

    @app.exception_handler(PrelabRequired)
    async def _handle_prelab_required(request: Request, _exc: PrelabRequired) -> JSONResponse:
        payload = build_blocked_payload(_resolve_language(request), BlockReason.PRELAB)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=payload,
        )

    @app.exception_handler(TokenBudgetExceeded)
    async def _handle_token_budget(request: Request, _exc: TokenBudgetExceeded) -> JSONResponse:
        payload = build_blocked_payload(_resolve_language(request), BlockReason.TOKEN_BUDGET)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=payload,
        )

    @app.exception_handler(RevealNotAllowed)
    async def _handle_reveal_not_allowed(_request: Request, exc: RevealNotAllowed) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": getattr(exc, "detail", "Hint reveal not allowed")},
        )