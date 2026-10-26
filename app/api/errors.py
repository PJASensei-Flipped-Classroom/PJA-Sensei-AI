from fastapi import Request
from fastapi.responses import JSONResponse
from app.domain.exceptions import PrelabRequired, TokenBudgetExceeded, UnknownConversation, UnknownMessage


async def prelab_required_handler(request: Request, exc: PrelabRequired):
    message = "Wymagane ukończenie pre-labu." if exc.language == "pl" else "Pre-lab completion required."
    return JSONResponse(
        status_code=403,
        content={
            "message_id": "prelab_required",
            "detail": message
        }
    )

async def token_budget_exceeded_handler(request: Request, exc: TokenBudgetExceeded):
    message = (
        f"Przekroczono budżet tokenów sesji ({exc.used}/{exc.limit})."
        if exc.language == "pl"
        else f"Session token budget exceeded ({exc.used}/{exc.limit})."
    )
    return JSONResponse(
        status_code=403,
        content={
            "message_id": "token_budget_exceeded",
            "detail": message,
            "limit": exc.limit,
            "used": exc.used,
        },
    )

async def unknown_conversation_handler(request: Request, exc: UnknownConversation):
    return JSONResponse(
        status_code=404,
        content={"message_id": "conversation_not_found", "detail": str(exc) or "Conversation not found"},
    )

async def unknown_message_handler(request: Request, exc: UnknownMessage):
    return JSONResponse(
        status_code=404,
        content={"message_id": "message_not_found", "detail": str(exc) or "Message not found"},
    )