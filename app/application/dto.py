from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List, Literal
from app.domain.sensei import SenseiConfig, CodeContext


class ConfigValidationRequest(BaseModel):
    config: Dict[str, Any]

class ConversationStartRequest(BaseModel):
    problem_description: Optional[str] = None
    config: SenseiConfig

class EventRequest(BaseModel):
    type: str
    meta: Optional[Dict[str, Any]] = None


class PrelabQuestionDTO(BaseModel):
    id: str
    question: str

class PrelabStatusResponse(BaseModel):
    enabled: bool
    passed: bool
    questions: List[PrelabQuestionDTO]
    attempts: int
    max_attempts: int
    score: int
    hint_after_fail: Optional[str]

class PrelabAnswer(BaseModel):
    id: str
    answer: str

class PrelabSubmitRequest(BaseModel):
    answers: List[PrelabAnswer]

class PrelabSubmitResponse(BaseModel):
    passed: bool
    score: int
    detail: str
    failed_ids: List[str]
    attempts: int
    unlocked: bool

class GoalProgressEntryDTO(BaseModel):
    goal: str
    status: Literal["not_started", "in_progress", "done"]

class NextCheckpointDTO(BaseModel):
    id: str
    after_goal: str
    hint: Optional[str] = None
    unlocked: bool

class MessageRequest(BaseModel):
    question: str = Field(min_length=1)
    code_context: Optional[CodeContext] = None
    client_message_id: Optional[str] = None

class MessageResponse(BaseModel):
    message_id: str
    answer: str
    prompt_score: int = Field(ge=1, le=10)
    prompt_feedback: str
    tokens_used: int
    penalty_applied: bool
    sources: List[str] = []
    suggested_next_step: str
    goal_progress: List[GoalProgressEntryDTO]
    lab_score: int = 0
    next_checkpoint: Optional[NextCheckpointDTO] = None
    model: str
    debug_info: Optional[Dict[str, Any]] = None

class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    status: str
    message_id: str
    rating: int