from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional, List
from app.domain.sensei import SenseiConfig

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