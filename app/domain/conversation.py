"""In-memory conversation aggregate."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.sensei import SenseiConfig

FRUSTRATION_THRESHOLD = 4
FRUSTRATION_STREAK = 3


def consecutive_low_scores(
    scores: list[int], threshold: int = FRUSTRATION_THRESHOLD
) -> int:
    count = 0
    for score in reversed(scores):
        if score <= threshold:
            count += 1
        else:
            break
    return count


def is_frustrated(scores: list[int]) -> bool:
    return consecutive_low_scores(scores) >= FRUSTRATION_STREAK


def recent_avg_score(scores: list[int]) -> float:
    if not scores:
        return 0.0
    recent = scores[-3:]
    return sum(recent) / len(recent)


def consecutive_low_enough(
    scores: list[int],
    n: int = FRUSTRATION_STREAK,
    threshold: int = FRUSTRATION_THRESHOLD,
) -> bool:
    if len(scores) < n:
        return False
    return all(s <= threshold for s in scores[-n:])


@dataclass
class Conversation:
    problem: str
    config: SenseiConfig
    messages: list[dict] = field(default_factory=list)
    prompt_scores: list[int] = field(default_factory=list)
    last_code: str = ""
    prelab_passed: bool = False
    prelab_attempts: int = 0
    last_prelab_score: float | None = None
    tokens_used_total: int = 0
    ide_events: list[dict[str, Any]] = field(default_factory=list)
    reveal_count: int = 0
    summary_generated: bool = False
    last_summary: dict[str, Any] | None = None
    goal_progress: list[dict[str, str]] = field(default_factory=list)
    unlocked_checkpoints: list[str] = field(default_factory=list)
    idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)
    pinned_identifiers: list[str] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_active_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def remember_identifiers(self, tokens: list[str], *, limit: int = 12) -> None:
        """Keep student-stated code identifiers across compression."""
        seen = {t.lower() for t in self.pinned_identifiers}
        for tok in tokens:
            key = tok.lower()
            if key in seen:
                continue
            seen.add(key)
            self.pinned_identifiers.append(tok)
            if len(self.pinned_identifiers) >= limit:
                break

    @property
    def is_frustrated(self) -> bool:
        return is_frustrated(self.prompt_scores)

    def touch(self) -> None:
        self.last_active_at = datetime.now(timezone.utc)

    def ensure_goal_progress_defaults(self) -> None:
        if self.goal_progress:
            return
        self.goal_progress = [
            {"goal": g, "status": "not_started"}
            for g in (self.config.learningContext.goals or [])
        ]
