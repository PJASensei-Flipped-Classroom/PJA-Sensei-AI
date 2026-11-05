from fastapi import Request
from fastapi.responses import JSONResponse
from app.domain.exceptions import PrelabRequired, TokenBudgetExceeded, UnknownConversation, UnknownMessage, \
    HintRevealForbidden, SsrfBlockedError


# Upstream LLM rate-limit exhausted after fallback → 503 (not client 429).
_LLM_RATE_LIMIT_RETRY_AFTER = "5"


async def llm_rate_limited_handler(request: Request, exc: Exception):
    from app.application.metrics import metrics

    metrics.inc_llm_rate_limited()
    return JSONResponse(
        status_code=503,
        content={
            "message_id": "llm_rate_limited",
            "detail": "Language model is temporarily rate-limited. Please retry shortly.",
        },
        headers={"Retry-After": _LLM_RATE_LIMIT_RETRY_AFTER},
    )


async def llm_unavailable_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=503,
        content={
            "message_id": "llm_unavailable",
            "detail": "Language model is temporarily unavailable. Please retry shortly.",
        },
        headers={"Retry-After": _LLM_RATE_LIMIT_RETRY_AFTER},
    )


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
async def hint_reveal_forbidden_handler(request: Request, exc: HintRevealForbidden):
    if exc.reason == "quota_exceeded":
        detail = (
            f"Wyczerpano limit wskazówek w tej sesji ({exc.hints_used}/{exc.max_hints})."
            if exc.language == "pl"
            else f"Hint quota exceeded for this session ({exc.hints_used}/{exc.max_hints})."
        )
    else:
        detail = (
            f"Wskazówka zablokowana: spróbuj najpierw samodzielnie rozwiązać problem (streak: {exc.streak}/{exc.required_streak})."
            if exc.language == "pl"
            else f"Hint locked: try solving the problem first (streak: {exc.streak}/{exc.required_streak})."
        )

    return JSONResponse(
        status_code=403,
        content={
            "message_id": "hint_reveal_forbidden",
            "reason": exc.reason,
            "detail": detail,
            "streak": exc.streak,
            "required_streak": exc.required_streak,
            "hints_used": exc.hints_used,
            "max_hints": exc.max_hints,
        },
    )
async def ssrf_blocked_handler(request: Request, exc: SsrfBlockedError):
    return JSONResponse(
        status_code=400,
        content={"message_id": "ssrf_blocked", "detail": exc.reason, "blocked_url": exc.url},
    )