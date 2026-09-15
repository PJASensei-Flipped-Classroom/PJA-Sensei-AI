"""Trasy obsługi wiadomości czatu (tryb synchroniczny, strumieniowy NDJSON oraz feedback)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
import logging
from typing import Any
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, status
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
    """Potwierdzenie zarejestrowania oceny studenta dla konkretnej wypowiedzi."""

    status: str = Field(default="recorded", description="Status operacji zapisu")
    message_id: str = Field(..., description="Identyfikator ocenionej wiadomości")
    rating: int = Field(..., description="Wartość liczbowa oceny")


def _build_telemetry_payload(conversation_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Buduje ujednolicony słownik ze statystykami tury czatu na potrzeby telemetrii."""
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
    stream_generator: AsyncIterator[str | bytes],
    conversation_id: str,
    request_id: str,
) -> AsyncIterator[str | bytes]:
    """Przekazuje linie NDJSON do klienta i wysyła telemetrię po dotarciu do zdarzenia 'final'."""
    is_completed = False
    try:
        async for chunk in stream_generator:
            yield chunk

            try:
                raw_text = chunk if isinstance(chunk, str) else chunk.decode("utf-8")
                event_data = json.loads(raw_text)

                if event_data.get("type") == "final":
                    is_completed = True
                    payload = _build_telemetry_payload(conversation_id, event_data)
                    await send_request_telemetry(payload, request_id=request_id)
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                # Pomijamy fragmenty niebędące pełnymi obiektami JSON
                continue

    except asyncio.CancelledError:
        logger.info("Klient zerwał połączenie strumieniowe [request_id=%s]", request_id)
        raise
    finally:
        if not is_completed:
            logger.debug("Strumień zakończony bez zdarzenia finalnego [request_id=%s]", request_id)


@router.get(
    "/conversations/{conversation_id}/messages",
    summary="Pobranie historii konwersacji",
)
async def list_messages(
    conversation_id: str,
    container: AppContainer = Depends(get_container),
) -> dict[str, Any]:
    """Zwraca dotychczasowy przebieg dialogu w sesji z pominięciem pól poufnych prelabu."""
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
    container: AppContainer = Depends(get_container),
) -> MessageResponse | JSONResponse:
    """Waliduje stan sesji, generuje kompletną odpowiedź i emituje telemetrię w tle."""
    _, early_response = await validate_message_request(
        conversation_id, request, background_tasks, container
    )
    if early_response is not None:
        return early_response

    req_id = request_id_var.get("-")
    result = await container.chat.send_message(conversation_id, request)

    background_tasks.add_task(
        send_request_telemetry,
        _build_telemetry_payload(conversation_id, result),
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
    container: AppContainer = Depends(get_container),
) -> StreamingResponse | JSONResponse:
    """Zwraca strumień tokenów NDJSON na żywo, a po evencie 'final' emituje telemetrię."""
    _, early_response = await validate_message_request(
        conversation_id, request, background_tasks, container
    )
    if early_response is not None:
        return early_response

    message_id = str(uuid.uuid4())
    req_id = request_id_var.get("-")
    stream_generator = container.stream.stream_message(conversation_id, request, message_id)

    response_headers = {
        "X-Message-Id": message_id,
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # Wyłącza buforowanie w Nginx dla płynnego streamingu
    }

    return StreamingResponse(
        _stream_with_telemetry(stream_generator, conversation_id, req_id),
        media_type="application/x-ndjson",
        headers=response_headers,
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
    """Zapisuje ocenę punktową i opcjonalny komentarz dydaktyczny studenta."""
    container.sessions.record_message_feedback(
        conversation_id,
        message_id,
        rating=feedback.rating,
        comment=feedback.comment,
    )
    return FeedbackResponse(message_id=message_id, rating=feedback.rating)