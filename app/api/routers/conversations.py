from fastapi import APIRouter, Depends, HTTPException, status
from app.application.dto import ConversationStartRequest, EventRequest
from app.application.session_service import SessionService
from app.domain.exceptions import UnknownConversation
from app.infrastructure.conversations_memory import InMemoryConversationRepository

from app.application.prelab_service import PrelabService
from app.application.dto import PrelabSubmitRequest

router = APIRouter(prefix="/conversations", tags=["Conversations"])

repo = InMemoryConversationRepository()
def get_session_service() -> SessionService:
    return SessionService(repo)
def get_prelab_service() -> PrelabService:
    return PrelabService(repo)

@router.post("")
def start_conversation(req: ConversationStartRequest, svc: SessionService = Depends(get_session_service)):
    conv = svc.start_conversation(req.config)
    return {
        "conversation_id": conv.id,
        "prelab_required": not conv.prelab_completed,
        "ide_restrictions": conv.config.ide_restrictions.model_dump(by_alias=True)
    }

@router.get("/{conv_id}")
def get_conversation(conv_id: str, svc: SessionService = Depends(get_session_service)):
    try:
        conv = svc.get_or_404(conv_id)
        return {
            "id": conv.id,
            "goal_progress": conv.goal_progress,
            "unlocked_checkpoints": conv.unlocked_checkpoints,
        }
    except UnknownConversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

@router.delete("/{conv_id}")
def delete_conversation(conv_id: str, svc: SessionService = Depends(get_session_service)):
    try:
        svc.delete(conv_id)
        return {"status": "deleted"}
    except UnknownConversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

@router.get("/{conv_id}/restrictions")
def get_restrictions(conv_id: str, svc: SessionService = Depends(get_session_service)):
    try:
        return svc.get_or_404(conv_id).config.ide_restrictions.model_dump(by_alias=True)
    except UnknownConversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

@router.get("/{conv_id}/export")
def export_conversation(conv_id: str, svc: SessionService = Depends(get_session_service)):
    try:
        return svc.export(conv_id)
    except UnknownConversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

@router.get("/{conv_id}/checkpoints")
def get_checkpoints(conv_id: str, svc: SessionService = Depends(get_session_service)):
    try:
        return {"unlocked": svc.get_or_404(conv_id).unlocked_checkpoints}
    except UnknownConversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")

@router.post("/{conv_id}/events")
def record_event(conv_id: str, req: EventRequest, svc: SessionService = Depends(get_session_service)):
    try:
        svc.record_event(conv_id, req.type, req.meta or {})
        return {"status": "recorded"}
    except UnknownConversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")


@router.get("/{conv_id}/prelab")
def get_prelab_status(
        conv_id: str,
        svc: SessionService = Depends(get_session_service),
        prelab_svc: PrelabService = Depends(get_prelab_service)
):
    conv = svc.get_or_404(conv_id)
    return prelab_svc.get_status(conv)


@router.post("/{conv_id}/prelab")
def submit_prelab(
        conv_id: str,
        req: PrelabSubmitRequest,
        svc: SessionService = Depends(get_session_service),
        prelab_svc: PrelabService = Depends(get_prelab_service)
):
    conv = svc.get_or_404(conv_id)
    return prelab_svc.submit(conv, req)


@router.post("/{conv_id}/messages")
def send_message(conv_id: str, svc: SessionService = Depends(get_session_service)):
    svc.ensure_prelab_passed(conv_id)

    from fastapi import HTTPException
    raise HTTPException(status_code=501, detail="chat in M3")