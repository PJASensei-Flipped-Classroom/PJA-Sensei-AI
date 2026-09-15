"""Trasy API zarządzające cyklem życia sesji konwersacji i kontraktem edytora IDE."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.api.deps import get_container
from app.api.middleware import request_id_var
from app.api.routers.config_validate import assert_sensei_config_valid
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


# --- Schematy odpowiedzi DTO ---

class StartConversationResponse(BaseModel):
    """Odpowiedź po zainicjalizowaniu sesji z informacjami wstępnymi dla IDE."""

    conversation_id: str
    prelab_required: bool
    ide_restrictions: dict[str, Any] | None


class IdeEventResponse(BaseModel):
    """Potwierdzenie odebrania i przetworzenia zdarzenia z edytora IDE."""

    status: str
    event: dict[str, Any]


# --- Narzędzia pomocnicze ---

def _resolve_attr(target: Any, *candidates: str) -> Any | None:
    """Pobiera pierwszy istniejący atrybut spośród kandydatów (obsługa snake_case vs camelCase)."""
    for attr in candidates:
        if (value := getattr(target, attr, None)) is not None:
            return value
    return None


# --- Trasy i kontrolery ---

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
    """Tworzy sesję konwersacyjną oraz asynchronicznie indeksuje materiały RAG w tle."""
    metrics.inc("requests_total")
    assert_sensei_config_valid(request.config)
    conv_id = container.sessions.start_conversation(
        request.problem_description,
        request.config,
    )

    # Elastyczne wyciąganie zagnieżdżonych struktur niezależnie od konwencji nazewnictwa
    learning_ctx = _resolve_attr(request.config, "learning_context", "learningContext")
    materials = _resolve_attr(learning_ctx, "reference_materials", "referenceMaterials")

    if materials:
        background_tasks.add_task(
            container.rag.load_materials,
            conv_id,
            materials,
        )

    pre_lab = _resolve_attr(request.config, "pre_lab", "preLab")
    is_prelab_required = bool(pre_lab and getattr(pre_lab, "enabled", False))

    restrictions = _resolve_attr(request.config, "ide_restrictions", "ideRestrictions")
    serialized_restrictions = restrictions.model_dump() if restrictions else None

    return StartConversationResponse(
        conversation_id=conv_id,
        prelab_required=is_prelab_required,
        ide_restrictions=serialized_restrictions,
    )


@router.get("/conversations/{conversation_id}", summary="Pobranie stanu sesji")
async def get_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Zwraca zagregowane metryki, stan modułu prelab oraz checkpointy sesji."""
    return container.sessions.get_session_state(conversation_id)


@router.get("/conversations/{conversation_id}/restrictions", summary="Pobranie ograniczeń edytora")
async def get_restrictions(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Zwraca zestaw zasad narzuconych na edytor (ideRestrictions)."""
    return container.sessions.get_restrictions(conversation_id)


@router.get("/conversations/{conversation_id}/export", summary="Eksport historii czatu")
async def export_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Eksportuje kompletną historię dialogu i parametry dydaktyczne do JSON-a."""
    return container.sessions.export_conversation(conversation_id)


@router.get("/conversations/{conversation_id}/checkpoints", summary="Pobranie kamieni milowych")
async def get_checkpoints(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Zwraca listę celów edukacyjnych wraz ze stanem ich ukończenia."""
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
    """Rejestruje akcję studenta w edytorze i emituje telemetrię do zewnętrznej kolejki."""
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
    """Zamyka sesję, zwalnia wektory RAG i asynchronicznie przesyła podsumowanie na webhook."""
    req_id = request_id_var.get("-")
    result = await container.sessions.delete_conversation(
        conversation_id,
        generate_summary_on_delete=True,
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
    """Weryfikuje reguły frustracji studenta i odblokowuje bezpośrednią podpowiedź techniczną."""
    return await container.chat.reveal_hint(conversation_id, payload)


@router.post("/conversations/{conversation_id}/summary", summary="Generowanie podsumowania sesji")
async def get_summary(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Generuje raport dydaktyczny z sesji i przekazuje go do systemu telemetrii."""
    req_id = request_id_var.get("-")
    summary = await container.summary.generate_summary(conversation_id)
    conversation = container.sessions.get_conversation_or_404(conversation_id)

    feedbacks = [
        msg["student_feedback"]
        for msg in conversation.messages
        if msg.get("role") == "assistant" and "student_feedback" in msg
    ]

    background_tasks.add_task(
        send_request_telemetry,
        {
            "event": "session_summary",
            "conversation_id": conversation_id,
            "summary": summary,
            "scores": conversation.prompt_scores,
            "feedbacks": feedbacks,
        },
        url=SUMMARY_WEBHOOK_URL,
        request_id=req_id,
    )
    return summary