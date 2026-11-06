from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import StreamingResponse

from app.api.deps import (
    get_chat_service,
    get_prelab_service,
    get_session_service,
)
from app.application.access import ensure_conversation_access, require_professor
from app.application.chat_service import ChatService
from app.application.dto import (
    ConversationStartRequest,
    EventRequest,
    FeedbackRequest,
    HintRevealResponse,
    MessageRequest,
    MessageResponse,
    PrelabSubmitRequest,
)
from app.application.prelab_service import PrelabService
from app.application.session_service import SessionService
from app.application.similarity import best_solution_match
from app.core.config import settings
from app.domain.conversation import Conversation

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class ForceHintRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reason: Optional[str] = Field(default="professor_override")
    custom_hint: Optional[str] = Field(default=None, alias="customHint")
    hint_level: Optional[str] = Field(default=None, alias="hintLevel")


class InterventionNoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class SimilarityRequest(BaseModel):
    code: Optional[str] = None


def _claims(request: Request) -> Optional[Dict[str, Any]]:
    return getattr(request.state, "jwt_claims", None)


def _load_owned(
    conv_id: str,
    request: Request,
    svc: SessionService,
) -> Conversation:
    conv = svc.get_or_404(conv_id)
    ensure_conversation_access(conv, _claims(request))
    return conv


def _require_professor_when_auth(request: Request) -> None:
    if not settings.AI_AUTH_ENABLED:
        return
    if not require_professor(_claims(request)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message_id": "forbidden",
                "detail": "Professor role required.",
            },
        )


@router.post("")
def start_conversation(
    req: ConversationStartRequest,
    request: Request,
    svc: SessionService = Depends(get_session_service),
    prelab_svc: PrelabService = Depends(get_prelab_service),
):
    claims = _claims(request) or {}
    conv, rag_preview = svc.start_conversation(
        req.config,
        owner_sub=claims.get("sub"),
        lab_id=claims.get("labId") or claims.get("lab_id"),
    )
    prelab_status = prelab_svc.get_status(conv)
    questions_list = conv.config.pre_lab.questions
    first_question = questions_list[0].question if questions_list else None
    fallback_prelab_q = (
        "Jaka adnotacja w Spring Boot oznacza klasę kontrolera REST?"
        if conv.config.language == "pl"
        else "Which Spring Boot annotation marks a class as a REST controller?"
    )

    return {
        "conversation_id": conv.id,
        "prelab_required": bool(conv.config.pre_lab.enabled),
        "prelab_question": first_question or fallback_prelab_q,
        "prelab": prelab_status,
        "ide_restrictions": conv.config.ide_restrictions.model_dump(by_alias=True),
        "rag_preview": rag_preview.model_dump(),
    }


@router.get("")
def list_conversations(
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    _require_professor_when_auth(request)
    items = svc.list_conversations()
    return {"conversations": items, "count": len(items)}


@router.post("/purge")
def purge_conversations(
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    _require_professor_when_auth(request)
    purged = svc.purge_old_sessions()
    return {"purged": purged}


@router.get("/professor/dashboard")
def professor_dashboard(
    request: Request,
    lab_id: Optional[str] = None,
    svc: SessionService = Depends(get_session_service),
):
    _require_professor_when_auth(request)
    return svc.lab_dashboard(lab_id=lab_id)


@router.get("/{conv_id}")
def get_conversation(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    # OLD: try/except UnknownConversation -> HTTPException(404)
    # Removed because: global unknown_conversation_handler already maps that exception to 404.
    conv = _load_owned(conv_id, request, svc)
    return {
        "id": conv.id,
        "goal_progress": conv.goal_progress,
        "lab_score": conv.calculate_lab_score(),
        "lab_completed": conv.all_goals_done(),
        "unlocked_checkpoints": conv.unlocked_checkpoints,
        "token_usage": conv.token_usage,
        "frustration_streak": conv.frustration_streak,
        "hints_revealed": conv.hints_revealed,
    }


@router.delete("/{conv_id}")
def delete_conversation(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    # OLD: try/except UnknownConversation -> HTTPException(404) (same on restrictions/export/checkpoints/events/summary/observe)
    # Removed because: redundant with the global UnknownConversation handler.
    _load_owned(conv_id, request, svc)
    return svc.delete(conv_id)


@router.get("/{conv_id}/restrictions")
def get_restrictions(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    return _load_owned(conv_id, request, svc).config.ide_restrictions.model_dump(by_alias=True)


@router.get("/{conv_id}/export")
def export_conversation(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    _load_owned(conv_id, request, svc)
    return svc.export(conv_id)


@router.get("/{conv_id}/checkpoints")
def get_checkpoints(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    return {"unlocked": _load_owned(conv_id, request, svc).unlocked_checkpoints}


@router.post("/{conv_id}/events")
def record_event(
    conv_id: str,
    req: EventRequest,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    _load_owned(conv_id, request, svc)
    return svc.record_event(conv_id, req.type, req.meta or {})


@router.get("/{conv_id}/prelab")
def get_prelab_status(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
    prelab_svc: PrelabService = Depends(get_prelab_service),
):
    conv = _load_owned(conv_id, request, svc)
    return prelab_svc.get_status(conv)


@router.post("/{conv_id}/summary")
def summarize_conversation(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    _load_owned(conv_id, request, svc)
    return svc.generate_summary(conv_id)


@router.post("/{conv_id}/prelab")
def submit_prelab(
    conv_id: str,
    req: PrelabSubmitRequest,
    request: Request,
    svc: SessionService = Depends(get_session_service),
    prelab_svc: PrelabService = Depends(get_prelab_service),
):
    conv = _load_owned(conv_id, request, svc)
    return prelab_svc.submit(conv, req)


@router.post("/{conv_id}/messages", response_model=MessageResponse)
def send_message(
    conv_id: str,
    req: MessageRequest,
    request: Request,
    svc: SessionService = Depends(get_session_service),
    chat_svc: ChatService = Depends(get_chat_service),
):
    _load_owned(conv_id, request, svc)
    return chat_svc.send_message(conv_id, req)


@router.get("/{conv_id}/messages")
def get_messages(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
    chat_svc: ChatService = Depends(get_chat_service),
):
    _load_owned(conv_id, request, svc)
    return {"messages": chat_svc.list_messages(conv_id)}


@router.post("/{conv_id}/messages/{message_id}/feedback")
def submit_feedback(
    conv_id: str,
    message_id: str,
    req: FeedbackRequest,
    request: Request,
    svc: SessionService = Depends(get_session_service),
    chat_svc: ChatService = Depends(get_chat_service),
):
    _load_owned(conv_id, request, svc)
    return chat_svc.add_feedback(conv_id, message_id, req)


@router.post("/{conv_id}/messages/stream")
def stream_message(
    conv_id: str,
    req: MessageRequest,
    request: Request,
    svc: SessionService = Depends(get_session_service),
    chat_svc: ChatService = Depends(get_chat_service),
):
    _load_owned(conv_id, request, svc)
    ndjson_iter = chat_svc.stream_message(conv_id, req)
    return StreamingResponse(ndjson_iter, media_type="application/x-ndjson")


@router.post("/{conv_id}/hints/reveal", response_model=HintRevealResponse)
def reveal_hint(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
    chat_svc: ChatService = Depends(get_chat_service),
):
    _load_owned(conv_id, request, svc)
    return chat_svc.reveal_hint(conv_id)


@router.post("/{conv_id}/hints/force", response_model=HintRevealResponse)
def force_hint(
    conv_id: str,
    request: Request,
    req: Optional[ForceHintRequest] = None,
    svc: SessionService = Depends(get_session_service),
    chat_svc: ChatService = Depends(get_chat_service),
):
    _load_owned(conv_id, request, svc)
    # OLD:
    # if settings.AI_AUTH_ENABLED and not require_professor(_claims(request)):
    #     raise HTTPException(..., detail="Professor role required for force-hint.")
    # Removed because: same gate as _require_professor_when_auth used by other professor routes.
    _require_professor_when_auth(request)
    reason = req.reason if req is not None else "professor_override"
    custom = req.custom_hint if req is not None else None
    level = req.hint_level if req is not None else None
    return chat_svc.force_reveal_hint(
        conv_id, reason=reason, custom_hint=custom, hint_level=level
    )


@router.post("/{conv_id}/notes")
def add_intervention_note(
    conv_id: str,
    body: InterventionNoteRequest,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    _require_professor_when_auth(request)
    _load_owned(conv_id, request, svc)
    claims = _claims(request) or {}
    return svc.add_intervention_note(conv_id, body.text, author_sub=claims.get("sub"))


@router.get("/{conv_id}/observe")
def observe_conversation(
    conv_id: str,
    request: Request,
    svc: SessionService = Depends(get_session_service),
):
    _require_professor_when_auth(request)
    return svc.observe(conv_id)


@router.post("/{conv_id}/similarity")
def similarity_check(
    conv_id: str,
    request: Request,
    body: Optional[SimilarityRequest] = None,
    svc: SessionService = Depends(get_session_service),
):
    _require_professor_when_auth(request)
    conv = _load_owned(conv_id, request, svc)
    code = (body.code if body and body.code else None) or ""
    if not code:
        for m in reversed(conv.messages):
            if m.role == "user" and m.code_context:
                code = (
                    m.code_context.get("currentCode")
                    or m.code_context.get("current_code")
                    or m.code_context.get("codeSnippet")
                    or ""
                )
                if code:
                    break
    result = best_solution_match(code, list(conv.config.solution_pack or []))
    return {
        "conversation_id": conv_id,
        "has_solution_pack": bool(conv.config.solution_pack),
        "code_chars": len(code or ""),
        **result,
        "disclaimer": "Heuristic flag only — not an academic misconduct verdict.",
    }
