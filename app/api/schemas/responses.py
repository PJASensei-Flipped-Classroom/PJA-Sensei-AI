"""HTTP response models."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class DebugInfo(BaseModel):
    is_frustrated: bool
    avg_score: float
    code_changed: bool


class SourceRef(BaseModel):
    title: str
    url: str
    timestamp: str | None = None
    page: int | None = None


class GoalProgressItem(BaseModel):
    goal: str
    status: Literal["not_started", "in_progress", "done"] = "not_started"


class MessageResponse(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    answer: str
    prompt_score: int
    prompt_feedback: str
    tokens_used: int
    is_cached: bool = False
    penalty_applied: bool = False
    sources: list[SourceRef] = Field(default_factory=list)
    suggested_next_step: str | None = None
    goal_progress: list[GoalProgressItem] = Field(default_factory=list)
    debug_info: DebugInfo | None = None
    client_message_id: str | None = None
