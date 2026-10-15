from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal
from datetime import datetime, timezone
from app.domain.sensei import SenseiConfig, CodeContext

class Conversation(BaseModel):
    id: str
    config: SenseiConfig
    messages: List[Dict[str, Any]] = []
    prelab_completed: bool = False
    goal_progress: Dict[str, Literal["not_started", "in_progress", "done"]] = {}
    unlocked_checkpoints: List[str] = []
    token_usage: int = 0
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prelab_attempts: int = 0

    def touch(self):
        self.last_activity = datetime.now(timezone.utc)