"""Conversation lifecycle and session contract routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, status
from pydantic import BaseModel

from app.api.deps import get_container
from app.api.middleware import request_id_var
from app.api.schemas.requests import (
    IdeEventRequest,
    RevealHintRequest,
    StartRequest,
)
from app.api.telemetry import send_request_telemetry
from app.application.container import AppContainer
from app.core.config import SUMMARY_WEBHOOK_URL
from app.core.metrics import metrics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversations"])


# --- Schematy odpowiedzi API ---

class StartConversationResponse(BaseModel):
    """Odpowiedź po utworzeniu sesji: id, czy wymagany prelab, ograniczenia IDE."""

    conversation_id: str
    prelab_required: bool
    ide_restrictions: dict[str, Any] | None


class IdeEventResponse(BaseModel):
    """Potwierdzenie przyjęcia zdarzenia telemetrycznego z edytora."""

    status: str
    event: dict[str, Any]


# --- Trasy ---

@router.post(
    "/conversations",
    response_model=StartConversationResponse,
    summary="Rozpoczęcie nowej sesji konwersacyjnej",
)
async def start_conversation(
    request: StartRequest,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
) -> StartConversationResponse:
    """Tworzy sesję i w tle ładuje materiały RAG, jeśli podano referenceMaterials."""
    metrics.inc("requests_total")
    conv_id = container.sessions.start_conversation(
        request.problem_description, request.config
    )

    # Obsługa snake_case i camelCase z klienta IDE
    learning_ctx = getattr(request.config, "learning_context", None) or getattr(
        request.config, "learningContext", None
    )
    materials = getattr(learning_ctx, "reference_materials", None) or getattr(
        learning_ctx, "referenceMaterials", None
    )

    if materials:
        background_tasks.add_task(
            container.rag.load_materials,
            conv_id,
            materials,
        )

    pre_lab = getattr(request.config, "pre_lab", None) or getattr(request.config, "preLab", None)
    is_prelab_required = bool(pre_lab and getattr(pre_lab, "enabled", False))

    ide_restrictions = getattr(request.config, "ide_restrictions", None) or getattr(
        request.config, "ideRestrictions", None
    )

    return StartConversationResponse(
        conversation_id=conv_id,
        prelab_required=is_prelab_required,
        ide_restrictions=ide_restrictions.model_dump() if ide_restrictions else None,
    )


@router.get("/conversations/{conversation_id}", summary="Pobranie stanu sesji")
async def get_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Zwraca zagregowany stan sesji (scores, prelab, tokens, checkpointy)."""
    return container.sessions.get_session_state(conversation_id)


@router.get("/conversations/{conversation_id}/restrictions", summary="Pobranie ograniczeń edytora")
async def get_restrictions(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Zwraca ideRestrictions skonfigurowane dla sesji."""
    return container.sessions.get_restrictions(conversation_id)


@router.get("/conversations/{conversation_id}/export", summary="Eksport historii czatu")
async def export_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Eksportuje historię i metadane sesji do payloadu JSON."""
    return container.sessions.export_conversation(conversation_id)


@router.get("/conversations/{conversation_id}/checkpoints", summary="Pobranie kamieni milowych")
async def get_checkpoints(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Lista checkpointów z informacją o odblokowaniu."""
    return container.sessions.get_checkpoints(conversation_id)


@router.post(
    "/conversations/{conversation_id}/events",
    response_model=IdeEventResponse,
    summary="Rejestracja zdarzenia z IDE",
)
async def post_ide_event(
    conversation_id: str,
    payload: IdeEventRequest,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Zapisuje zdarzenie IDE (copy/paste/file) i opcjonalnie wysyła telemetrię."""
    req_id = request_id_var.get("-")
    result = container.sessions.record_ide_event(conversation_id, payload)

    background_tasks.add_task(
        send_request_telemetry,
        {
            "event": "ide_event",
            "conversation_id": conversation_id,
            **result.get("event", {}),
        },
        request_id=req_id,
    )
    return result


@router.delete("/conversations/{conversation_id}", summary="Usunięcie sesji i rozliczenie podsumowania")
async def delete_conversation(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Soft-delete: generuje summary (jeśli możliwe) i czyści dane sesji/RAG."""
    req_id = request_id_var.get("-")
    result = await container.sessions.delete_conversation(
        conversation_id, generate_summary_on_delete=True
    )

    if summary := result.get("summary"):
        background_tasks.add_task(
            send_request_telemetry,
            {
                "event": "session_summary",
                "conversation_id": conversation_id,
                "summary": summary,
                "soft_close": True,
            },
            url=SUMMARY_WEBHOOK_URL,
            request_id=req_id,
        )
    return result


@router.post("/conversations/{conversation_id}/hints/reveal", summary="Odsłonięcie podpowiedzi")
async def reveal_hint(
    conversation_id: str,
    payload: RevealHintRequest,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Mocniejsza podpowiedź po spełnieniu bramki frustracji / limitu reveal."""
    # Wyjątki domenowe (UnknownConversation, PrelabRequired, RevealNotAllowed) 
    # są mapowane automatycznie przez globalny ExceptionHandler FastAPI
    return await container.chat.reveal_hint(conversation_id, payload)


@router.post("/conversations/{conversation_id}/summary", summary="Generowanie podsumowania sesji")
async def get_summary(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Generuje podsumowanie dydaktyczne i opcjonalnie wysyła je na webhook."""
    req_id = request_id_var.get("-")
    summary = await container.summary.generate_summary(conversation_id)
    conversation = container.sessions.get_conversation_or_404(conversation_id)

    scores = conversation.prompt_scores
    feedbacks = [
        m["student_feedback"]
        for m in conversation.messages
        if m.get("role") == "assistant" and "student_feedback" in m
    ]

    background_tasks.add_task(
        send_request_telemetry,
        {
            "event": "session_summary",
            "conversation_id": conversation_id,
            "summary": summary,
            "scores": scores,
            "feedbacks": feedbacks,
        },
        url=SUMMARY_WEBHOOK_URL,
        request_id=req_id,
    )
    return summary