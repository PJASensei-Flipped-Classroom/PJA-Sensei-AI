from fastapi import APIRouter, Depends, HTTPException, status
from starlette.responses import StreamingResponse

from app.application.chat_service import ChatService
from app.application.dto import ConversationStartRequest, EventRequest, MessageRequest, MessageResponse, FeedbackRequest
from app.application.session_service import SessionService
from app.domain.exceptions import UnknownConversation
from app.domain.ports import LlmPort
from app.infrastructure.conversations_memory import InMemoryConversationRepository
from app.infrastructure.llm_openai import OpenAiCompatibleLlmAdapter

from app.application.prelab_service import PrelabService
from app.application.dto import PrelabSubmitRequest

router = APIRouter(prefix="/conversations", tags=["Conversations"])



repo = InMemoryConversationRepository()
def get_session_service() -> SessionService:
    return SessionService(repo)
def get_prelab_service() -> PrelabService:
    return PrelabService(repo)

llm_adapter = OpenAiCompatibleLlmAdapter()
def get_llm_port() -> LlmPort:
    return llm_adapter
def get_chat_service(
    svc: SessionService = Depends(get_session_service),
    llm: LlmPort = Depends(get_llm_port),
) -> ChatService:
    return ChatService(repo=repo, session_svc=svc, llm=llm)

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
            "lab_score": conv.calculate_lab_score(),
            "lab_completed": conv.all_goals_done(),
            "unlocked_checkpoints": conv.unlocked_checkpoints,
            "token_usage": conv.token_usage,
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


@router.post("/{conv_id}/messages", response_model=MessageResponse)
def send_message(
    conv_id: str,
    req: MessageRequest,
    chat_svc: ChatService = Depends(get_chat_service),
):
    return chat_svc.send_message(conv_id, req)

@router.get("/{conv_id}/messages")
def get_messages(conv_id: str, chat_svc: ChatService = Depends(get_chat_service)):
    return {"messages": chat_svc.list_messages(conv_id)}

@router.post("/{conv_id}/messages/{message_id}/feedback")
def submit_feedback(
    conv_id: str,
    message_id: str,
    req: FeedbackRequest,
    chat_svc: ChatService = Depends(get_chat_service),
):
    return chat_svc.add_feedback(conv_id, message_id, req)

@router.post("/{conv_id}/messages/stream")
def stream_message(
    conv_id: str,
    req: MessageRequest,
    chat_svc: ChatService = Depends(get_chat_service),
):
    ndjson_iter = chat_svc.stream_message(conv_id, req)
    return StreamingResponse(ndjson_iter, media_type="application/x-ndjson")

