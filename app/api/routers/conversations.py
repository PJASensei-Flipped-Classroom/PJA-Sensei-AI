"""Conversation lifecycle and session contract routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.adapters.webhooks import send_telemetry_webhook
from app.api.deps import get_container
from app.api.middleware import request_id_var
from app.api.schemas.requests import (
    IdeEventRequest,
    RevealHintRequest,
    ReviewRequest,
    StartRequest,
)
from app.application.container import AppContainer
from app.core.config import SUMMARY_WEBHOOK_URL
from app.core.metrics import metrics
from app.domain.exceptions import (
    PrelabRequired,
    RevealNotAllowed,
    UnknownConversation,
)

router = APIRouter(tags=["conversations"])


async def _webhook(payload: dict, url: str | None = None) -> None:
    await send_telemetry_webhook(
        payload, url, request_id=request_id_var.get("-")
    )


@router.post("/conversations")
async def start_conversation(
    request: StartRequest,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
):
    metrics.inc("requests_total")
    conv_id = container.sessions.start_conversation(
        request.problem_description, request.config
    )

    if request.config.learningContext.referenceMaterials:
        background_tasks.add_task(
            container.rag.load_materials,
            conv_id,
            request.config.learningContext.referenceMaterials,
        )

    return {
        "conversation_id": conv_id,
        "prelab_required": bool(
            request.config.preLab and request.config.preLab.enabled
        ),
        "ideRestrictions": (
            request.config.ideRestrictions.model_dump()
            if request.config.ideRestrictions
            else None
        ),
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
):
    return container.sessions.get_session_state(conversation_id)


@router.get("/conversations/{conversation_id}/restrictions")
async def get_restrictions(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
):
    return container.sessions.get_restrictions(conversation_id)


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
):
    return container.sessions.export_conversation(conversation_id)


@router.get("/conversations/{conversation_id}/checkpoints")
async def get_checkpoints(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
):
    return container.sessions.get_checkpoints(conversation_id)


@router.post(
    "/conversations/{conversation_id}/goals/assess",
    tags=["experimental"],
)
async def assess_goals(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
):
    try:
        return await container.goals.assess_goals(conversation_id)
    except UnknownConversation:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/conversations/{conversation_id}/review",
    tags=["experimental"],
)
async def review_code(
    conversation_id: str,
    payload: ReviewRequest,
    container: AppContainer = Depends(get_container),
):
    try:
        return await container.review.review_code(conversation_id, payload)
    except (UnknownConversation, PrelabRequired):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/conversations/{conversation_id}/events")
async def post_ide_event(
    conversation_id: str,
    payload: IdeEventRequest,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
):
    result = container.sessions.record_ide_event(conversation_id, payload)
    background_tasks.add_task(
        _webhook,
        {
            "event": "ide_event",
            "conversation_id": conversation_id,
            **result["event"],
        },
    )
    return result


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
):
    result = await container.sessions.delete_conversation(
        conversation_id, soft_summary=True
    )
    if result.get("summary"):
        background_tasks.add_task(
            _webhook,
            {
                "event": "session_summary",
                "conversation_id": conversation_id,
                "summary": result["summary"],
                "soft_close": True,
            },
            SUMMARY_WEBHOOK_URL,
        )
    return result


@router.post(
    "/conversations/{conversation_id}/hints/reveal",
    tags=["experimental"],
)
async def reveal_hint(
    conversation_id: str,
    payload: RevealHintRequest,
    container: AppContainer = Depends(get_container),
):
    try:
        return await container.chat.reveal_hint(conversation_id, payload)
    except (UnknownConversation, PrelabRequired, RevealNotAllowed):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/conversations/{conversation_id}/summary")
async def get_summary(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    container: AppContainer = Depends(get_container),
):
    summary = await container.summary.generate_summary(conversation_id)
    conversation = container.conversations.get(conversation_id)
    scores = conversation.prompt_scores if conversation else []
    feedbacks = [
        m["student_feedback"]
        for m in (conversation.messages if conversation else [])
        if m.get("role") == "assistant" and "student_feedback" in m
    ]
    background_tasks.add_task(
        _webhook,
        {
            "event": "session_summary",
            "conversation_id": conversation_id,
            "summary": summary,
            "scores": scores,
            "feedbacks": feedbacks,
        },
        SUMMARY_WEBHOOK_URL,
    )
    return summary
