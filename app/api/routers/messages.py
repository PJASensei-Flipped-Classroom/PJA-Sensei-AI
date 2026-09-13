"""Chat message routes (sync, stream, regenerate, feedback)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.adapters.webhooks import send_telemetry_webhook
from app.api.deps import get_container, validate_message_request
from app.api.guards import require_conversation
from app.api.middleware import request_id_var
from app.api.schemas.requests import FeedbackRequest, MessageRequest
from app.api.schemas.responses import MessageResponse
from app.application.container import AppContainer
from app.domain.exceptions import (
    PrelabRequired,
    TokenBudgetExceeded,
    UnknownConversation,
)

router = APIRouter(tags=["messages"])


async def _webhook(payload: dict, url: str | None = None) -> None:
    await send_telemetry_webhook(
        payload, url, request_id=request_id_var.get("-")
    )


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
):
    return container.sessions.get_message_history(conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
)
async def send_message(
    conversation_id: str,
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    container: AppContainer = Depends(get_container),
):
    _, error_response = await validate_message_request(
        conversation_id, request, http_request, background_tasks, container
    )
    if error_response:
        return error_response

    try:
        result = await container.chat.send_message(conversation_id, request)
        background_tasks.add_task(
            _webhook,
            {
                "event": "message",
                "conversation_id": conversation_id,
                "message_id": result["message_id"],
                "prompt_score": result["prompt_score"],
                "tokens_used": result["tokens_used"],
                "is_cached": result["is_cached"],
                "penalty_applied": result.get("penalty_applied", False),
            },
        )
        return MessageResponse(**result)
    except (UnknownConversation, PrelabRequired, TokenBudgetExceeded):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    container: AppContainer = Depends(get_container),
):
    _, error_response = await validate_message_request(
        conversation_id, request, http_request, background_tasks, container
    )
    if error_response:
        return error_response

    msg_id = str(uuid.uuid4())
    return StreamingResponse(
        container.stream.stream_message(conversation_id, request, msg_id),
        media_type="application/x-ndjson",
        headers={"X-Message-Id": msg_id},
    )


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/regenerate",
    response_model=MessageResponse,
    tags=["experimental"],
)
async def regenerate_message(
    conversation_id: str,
    message_id: str,
    container: AppContainer = Depends(get_container),
):
    try:
        result = await container.chat.regenerate_message(
            conversation_id, message_id
        )
        return MessageResponse(**result)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (UnknownConversation, PrelabRequired, TokenBudgetExceeded):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/feedback"
)
async def rate_message(
    conversation_id: str,
    message_id: str,
    feedback: FeedbackRequest,
    container: AppContainer = Depends(get_container),
):
    conversation = require_conversation(container, conversation_id)
    target_msg = next(
        (m for m in conversation.messages if m.get("message_id") == message_id),
        None,
    )
    if not target_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    target_msg["student_feedback"] = {
        "rating": feedback.rating,
        "comment": feedback.comment,
    }
    conversation.touch()
    return {"status": "success", "message_id": message_id}
