from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.core.metrics import metrics

if TYPE_CHECKING:
    from app.application.container import AppContainer


class GoalsService:
    def __init__(self, app: AppContainer) -> None:
        self._app = app

    def get_checkpoints(self, conversation_id: str) -> dict:
        return self._app.sessions.get_checkpoints(conversation_id)

    async def assess_goals(self, conversation_id: str) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        conversation.ensure_goal_progress_defaults()
        lang = conversation.config.language
        goals = conversation.config.learningContext.goals or []
        history_text = "\n".join(
            f"{m.get('role')}: {str(m.get('content') or '')[:400]}"
            for m in conversation.messages[-20:]
        )
        prompt = f"""
Assess student progress against learning goals from conversation history.
Language: {"English" if lang == "en" else "Polish"}.
Goals: {json.dumps(goals, ensure_ascii=False)}
History excerpt:
{history_text}

Return JSON:
{{"goal_progress": [{{"goal": "...", "status": "not_started|in_progress|done"}}], "notes": "short"}}
Use only the provided goals. No solution code.
"""
        try:
            response = await self._app.client.chat.completions.create(
                model=self._app.llm.model_for(conversation),
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=350,
                temperature=0.2,
            )
            data = json.loads(response.choices[0].message.content or "{}")
        except Exception as e:
            metrics.inc("llm_errors")
            data = {
                "goal_progress": conversation.goal_progress,
                "notes": str(e),
            }
        progress = []
        for item in data.get("goal_progress") or []:
            if not isinstance(item, dict):
                continue
            goal = str(item.get("goal") or "").strip()
            status = str(item.get("status") or "not_started").strip()
            if status not in ("not_started", "in_progress", "done"):
                status = "not_started"
            if goal:
                progress.append({"goal": goal, "status": status})
        if not progress:
            progress = list(conversation.goal_progress)
        conversation.goal_progress = progress
        self._app.chat.remember_goal_progress(conversation, {"goal_progress": progress})
        conversation.touch()
        return {
            "conversation_id": conversation_id,
            "goal_progress": progress,
            "notes": data.get("notes"),
            "checkpoints": self._app.sessions.get_checkpoints(conversation_id)[
                "checkpoints"
            ],
        }
