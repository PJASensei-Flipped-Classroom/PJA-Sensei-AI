"""HTTP request bodies."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.sensei import CodeContext, SenseiConfig


class PreLabAnswerItem(BaseModel):
    id: str
    answer: str


class PreLabSubmitRequest(BaseModel):
    answers: list[PreLabAnswerItem]


class FeedbackRequest(BaseModel):
    rating: int
    comment: str | None = None


class StartRequest(BaseModel):
    problem_description: str
    config: SenseiConfig


class MessageRequest(BaseModel):
    question: str
    code_context: CodeContext
    client_message_id: str | None = None


class IdeEventRequest(BaseModel):
    type: Literal["copy_blocked", "file_opened", "paste_attempt"]
    meta: dict[str, Any] = Field(default_factory=dict)


class ValidateConfigRequest(BaseModel):
    config: dict


class RevealHintRequest(BaseModel):
    code_context: CodeContext | None = None
    focus: str | None = None


class ReviewRequest(BaseModel):
    code_context: CodeContext
    focus: str | None = None
