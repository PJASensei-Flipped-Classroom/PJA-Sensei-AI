"""Build Spring-ready grade sync payloads (prepared now; POST later by Spring)."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from app.domain.conversation import Conversation

GRADE_SCHEMA_VERSION = "1.0"


def build_grade_sync_payload(
    conv: Conversation,
    *,
    trigger: str,
    summary_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stable contract for the future Spring Boot backend.
    AI stores/emits this; Spring will pull or receive via webhook later.
    """
    penalties = sum(
        1
        for m in conv.messages
        if m.role == "assistant" and m.penalty_applied
    )
    return {
        "schema_version": GRADE_SCHEMA_VERSION,
        "event": "grade_sync_prepared",
        "trigger": trigger,
        "prepared_at": time.time(),
        "conversation_id": conv.id,
        "owner_sub": conv.owner_sub,
        "lab_id": conv.lab_id,
        "lab_score": conv.calculate_lab_score(),
        "completed": conv.all_goals_done(),
        "goal_progress": dict(conv.goal_progress),
        "hints_used": conv.hints_revealed,
        "highest_hint_level": conv.highest_hint_level,
        "penalties_count": penalties,
        "tokens_used": conv.token_usage,
        "messages_count": len(conv.messages),
        "frustration_streak": conv.frustration_streak,
        "summary": summary_text
        or (conv.summary or {}).get("summary")
        or (conv.summary or {}).get("text"),
    }
