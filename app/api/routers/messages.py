"""Chat message routes (sync, stream, feedback)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_container, validate_message_request
from app.api.middleware import request_id_var
from app.api.schemas.requests import FeedbackRequest, MessageRequest
from app.api.schemas.responses import MessageResponse
from app.api.telemetry import send_request_telemetry
from app.application.container import AppContainer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["messages"])


class FeedbackResponse(BaseModel):
    """Potwierdzenie zapisania oceny studenta dla konkretnej wiadomości."""

    status: str = Field(default="recorded")
    message_id: str
    rating: int


def _message_telemetry_payload(conversation_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Buduje payload webhooka telemetrycznego po zakończeniu tury czatu."""
    return {
        "event": "message",
        "conversation_id": conversation_id,
        "message_id": result.get("message_id"),
        "prompt_score": result.get("prompt_score"),
        "tokens_used": result.get("tokens_used"),
        "is_cached": result.get("is_cached", False),
        "penalty_applied": result.get("penalty_applied", False),
    }


async def _stream_with_telemetry(
    lines: AsyncIterator[str | bytes],
    conversation_id: str,
    request_id: str,
) -> AsyncIterator[str | bytes]:
    """Forward NDJSON lines and emit telemetry on the final event."""
    final_event_sent = False
    try:
        async for line in lines:
            yield line
            try:
                raw_text = line if isinstance(line, str) else line.decode("utf-8")
                evt = json.loads(raw_text)
                if evt.get("type") == "final":
                    final_event_sent = True
                    await send_request_telemetry(
                        _message_telemetry_payload(conversation_id, evt),
                        request_id=request_id,
                    )
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                continue
    except asyncio.CancelledError:
        logger.info("Client cancelled stream [request_id=%s]", request_id)
        raise
    finally:
        if not final_event_sent:
            logger.debug("Stream ended without final [request_id=%s]", request_id)


@router.get(
    "/conversations/{conversation_id}/messages",
    summary="Pobranie historii konwersacji",
)
async def list_messages(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Zwraca historię wiadomości sesji (bez sekretów prelab)."""
    return container.sessions.get_message_history(conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=None,
    summary="Wysłanie wiadomości w trybie blokującym",
)
async def send_message(
    conversation_id: str,
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    container: AppContainer = Depends(get_container),
) -> MessageResponse | JSONResponse:
    """Waliduje żądanie, wywołuje ChatService i emituje telemetrię w tle."""
    _, early = await validate_message_request(
        conversation_id, request, http_request, background_tasks, container
    )
    if early is not None:
        return early

    req_id = request_id_var.get("-")
    result = await container.chat.send_message(conversation_id, request)

    background_tasks.add_task(
        send_request_telemetry,
        _message_telemetry_payload(conversation_id, result),
        None,
        request_id=req_id,
    )
    return MessageResponse(**result)


@router.post(
    "/conversations/{conversation_id}/messages/stream",
    response_model=None,
    summary="Wysłanie wiadomości w trybie strumieniowym (NDJSON)",
)
async def send_message_stream(
    conversation_id: str,
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    container: AppContainer = Depends(get_container),
) -> StreamingResponse | JSONResponse:
    """Strumień NDJSON: tokeny live + final; telemetria po zdarzeniu final."""
    _, early = await validate_message_request(
        conversation_id, request, http_request, background_tasks, container
    )
    if early is not None:
        return early

    msg_id = str(uuid.uuid4())
    req_id = request_id_var.get("-")

    generator = container.stream.stream_message(conversation_id, request, msg_id)

    return StreamingResponse(
        _stream_with_telemetry(generator, conversation_id, req_id),
        media_type="application/x-ndjson",
        headers={
            "X-Message-Id": msg_id,
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Zapis oceny studenta dla danej odpowiedzi",
)
async def rate_message(
    conversation_id: str,
    message_id: str,
    feedback: FeedbackRequest,
    container: AppContainer = Depends(get_container),
) -> FeedbackResponse:
    """Zapisuje rating/komentarz studenta poprzez SessionService."""
    container.sessions.record_message_feedback(
        conversation_id,
        message_id,
        rating=feedback.rating,
        comment=feedback.comment,
    )
    return FeedbackResponse(message_id=message_id, rating=feedback.rating)
