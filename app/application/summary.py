from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.application.container import AppContainer

logger = logging.getLogger(__name__)


class SummaryService:
    def __init__(self, app: AppContainer) -> None:
        self._app = app

    async def generate_summary(self, conversation_id: str) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        conversation.touch()

        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in conversation.messages
        )
        scores = conversation.prompt_scores
        avg_score = sum(scores) / len(scores) if scores else 0
        lang = conversation.config.language
        criteria = conversation.config.evaluationCriteria
        events_summary = {
            "copy_blocked": sum(
                1 for e in conversation.ide_events if e.get("type") == "copy_blocked"
            ),
            "paste_attempt": sum(
                1 for e in conversation.ide_events if e.get("type") == "paste_attempt"
            ),
            "file_opened": sum(
                1 for e in conversation.ide_events if e.get("type") == "file_opened"
            ),
            "reveals": conversation.reveal_count,
        }

        feedbacks = []
        for m in conversation.messages:
            if m.get("role") == "assistant" and "student_feedback" in m:
                feedbacks.append(
                    f"rating={m['student_feedback']['rating']}, "
                    f"comment={m['student_feedback'].get('comment', '')}"
                )

        criteria_text = (
            "\n".join(f"- {c}" for c in criteria)
            if criteria
            else "- Clarity, code-context use, progress on goals"
        )
        feedbacks_text = "\n".join(feedbacks) if feedbacks else "none"

        prompt = f"""
Summarize student work for lecturer.
Language: {"English" if lang == "en" else "Polish"}.
Assignment: {conversation.problem}
Criteria:
{criteria_text}
History:
{history_text}
Scores: {scores} (avg {avg_score:.2f})
Student feedbacks: {feedbacks_text}
IDE events: {events_summary}

Return JSON with keys:
mastery_score, student_actions, agent_evaluation_of_student,
student_evaluation_of_agent, professors_summary
"""
        try:
            response = await self._app.client.chat.completions.create(
                model=self._app.llm.model_for(conversation),
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            summary = json.loads(raw)
        except Exception as e:
            logger.error("Error generating summary: %s", e)
            summary = {
                "mastery_score": 0,
                "student_actions": "",
                "agent_evaluation_of_student": "",
                "student_evaluation_of_agent": "",
                "professors_summary": str(e),
            }
        conversation.summary_generated = True
        summary["ide_events"] = events_summary
        conversation.last_summary = summary
        return summary
