from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional
from datetime import datetime, timezone
from app.domain.sensei import SenseiConfig

GoalStatus = Literal["not_started", "in_progress", "done"]

class MessageFeedback(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessage(BaseModel):
    message_id: str
    role: Literal["user", "assistant"]
    content: str
    client_message_id: Optional[str] = None
    code_context: Optional[Dict[str, Any]] = None
    prompt_score: Optional[int] = None
    prompt_feedback: Optional[str] = None
    penalty_applied: Optional[bool] = None
    suggested_next_step: Optional[str] = None
    tokens_used: int = 0
    model: Optional[str] = None
    feedback: Optional[MessageFeedback] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Conversation(BaseModel):
    id: str
    config: SenseiConfig
    messages: List[ChatMessage] = []
    prelab_completed: bool = False
    goal_progress: Dict[str, Literal["not_started", "in_progress", "done"]] = {}
    unlocked_checkpoints: List[str] = []
    token_usage: int = 0
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prelab_attempts: int = 0
    idempotency_cache: Dict[str, Dict[str, Any]] = {}

    def touch(self):
        self.last_activity = datetime.now(timezone.utc)

    def calculate_lab_score(self) -> int:
        total = len(self.config.learning_context.goals)
        if total == 0:
            return 0
        done_count = sum(1 for status in self.goal_progress.values() if status == "done")
        return round(10 * done_count / total)

    def all_goals_done(self) -> bool:
        total = len(self.config.learning_context.goals)
        if total == 0:
            return False
        return all(
            self.goal_progress.get(g.id) == "done"
            for g in self.config.learning_context.goals
        )