from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application.container import AppContainer


class AnalyticsService:
    def __init__(self, app: AppContainer) -> None:
        self._app = app

    def build_correlations(self) -> dict:
        self._app.sessions.purge_stale_conversations()
        rows = []
        for cid, conv in self._app.conversations.items():
            ratings = [
                m["student_feedback"]["rating"]
                for m in conv.messages
                if m.get("role") == "assistant" and "student_feedback" in m
            ]
            penalties = sum(
                1
                for m in conv.messages
                if m.get("role") == "assistant" and m.get("penalty_applied")
            )
            avg_prompt = (
                sum(conv.prompt_scores) / len(conv.prompt_scores)
                if conv.prompt_scores
                else 0.0
            )
            avg_rating = sum(ratings) / len(ratings) if ratings else None
            copy_blocks = sum(
                1 for e in conv.ide_events if e.get("type") == "copy_blocked"
            )
            rows.append(
                {
                    "conversation_id": cid,
                    "turns": len(conv.prompt_scores),
                    "avg_prompt_score": round(avg_prompt, 2),
                    "avg_student_rating": (
                        round(avg_rating, 2) if avg_rating is not None else None
                    ),
                    "student_ratings_count": len(ratings),
                    "penalty_count": penalties,
                    "copy_blocked_count": copy_blocks,
                    "ide_events": len(conv.ide_events),
                    "problem": conv.problem[:120],
                }
            )

        scored = [r for r in rows if r["turns"] > 0]
        rated = [r for r in rows if r["avg_student_rating"] is not None]
        return {
            "conversations": rows,
            "globals": {
                "conversation_count": len(rows),
                "avg_prompt_score": (
                    round(sum(r["avg_prompt_score"] for r in scored) / len(scored), 2)
                    if scored
                    else 0.0
                ),
                "avg_student_rating": (
                    round(
                        sum(r["avg_student_rating"] for r in rated) / len(rated), 2
                    )
                    if rated
                    else None
                ),
            },
        }
