"""In-memory conversation aggregate (Domain Model)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from app.domain.sensei import SenseiConfig

FRUSTRATION_THRESHOLD = 4
FRUSTRATION_STREAK = 3
REVEAL_LOW_STREAK = 2

GoalStatus = Literal["not_started", "in_progress", "done"]


@dataclass(slots=True, frozen=True)
class GoalProgress:
    """Wartość opisująca stan realizacji celu dydaktycznego."""
    goal: str
    status: GoalStatus = "not_started"

    def to_dict(self) -> dict[str, str]:
        return {"goal": self.goal, "status": self.status}


def consecutive_low_scores(
    scores: list[int], threshold: int = FRUSTRATION_THRESHOLD
) -> int:
    """Zlicza, ile ostatnich ocen z rzędu było mniejszych bądź równych progowi."""
    count = 0
    for score in reversed(scores):
        if score <= threshold:
            count += 1
        else:
            break
    return count


def is_frustrated(scores: list[int]) -> bool:
    """Określa, czy student wykazuje chroniczną frustrację / utknięcie."""
    return consecutive_low_scores(scores, FRUSTRATION_THRESHOLD) >= FRUSTRATION_STREAK


def recent_avg_score(scores: list[int], window: int = 3) -> float:
    """Wylicza średnią ocen z ostatniego okna zapytań."""
    if not scores:
        return 0.0
    recent = scores[-window:]
    return sum(recent) / len(recent)


def reveal_gate_open(scores: list[int], *, is_frustrated_now: bool) -> bool:
    """Sprawdza, czy kryteria uprawniają studenta do odsłonięcia mocniejszej wskazówki."""
    return is_frustrated_now or consecutive_low_scores(scores, FRUSTRATION_THRESHOLD) >= REVEAL_LOW_STREAK


@dataclass(slots=True)
class Conversation:
    """Agregat domenowy reprezentujący pełny stan sesji laboratoryjnej."""

    problem: str
    config: SenseiConfig
    messages: list[dict[str, Any]] = field(default_factory=list)
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
        """Zapamiętuje kluczowe identyfikatory zmiennych nazwane przez studenta."""
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
        """Stan frustracji wyliczany na bieżąco z historii promptów."""
        return is_frustrated(self.prompt_scores)

    def touch(self) -> None:
        """Odświeża znacznik czasu ostatniej aktywności."""
        self.last_active_at = datetime.now(timezone.utc)

    def ensure_goal_progress_defaults(self) -> None:
        """Inicjalizuje stan celów dydaktycznych na podstawie konfiguracji zadania."""
        if self.goal_progress:
            return
        goals = self.config.learning_context.goals or []
        self.goal_progress = [
            GoalProgress(goal=g, status="not_started").to_dict()
            for g in goals
        ]