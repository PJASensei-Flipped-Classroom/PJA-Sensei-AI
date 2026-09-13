from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.api.schemas.requests import ReviewRequest
from app.application.prompts import format_code_context_block
from app.application.response_pipeline import contains_revealed_code
from app.core.metrics import metrics

if TYPE_CHECKING:
    from app.application.container import AppContainer


class ReviewService:
    def __init__(self, app: AppContainer) -> None:
        self._app = app

    async def review_code(self, conversation_id: str, payload: ReviewRequest) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        self._app.sessions.ensure_prelab_passed(conversation)
        lang = conversation.config.language
        ctx = format_code_context_block(payload.code_context, language=lang)
        focus = payload.focus or ""
        prompt = f"""
You are a Socratic code reviewer. Do NOT provide a full patch or complete solution.
Language: {"English" if lang == "en" else "Polish"}.
Assignment: {conversation.problem}
Focus: {focus}
Student context:
{ctx}

Return JSON:
{{
  "findings": [
    {{
      "severity": "error|warning|info",
      "message": "what looks wrong conceptually",
      "socratic_question": "guiding question",
      "file": "optional path",
      "line": null
    }}
  ],
  "suggested_next_step": "one next action"
}}
"""
        try:
            response = await self._app.client.chat.completions.create(
                model=self._app.llm.model_for(conversation),
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=400,
                temperature=0.4,
            )
            data = json.loads(response.choices[0].message.content or "{}")
        except Exception as e:
            metrics.inc("llm_errors")
            data = {
                "findings": [
                    {
                        "severity": "info",
                        "message": str(e),
                        "socratic_question": None,
                    }
                ],
                "suggested_next_step": None,
            }
        findings = []
        for item in data.get("findings") or []:
            if not isinstance(item, dict):
                continue
            msg = str(item.get("message") or "").strip()
            if contains_revealed_code(msg):
                msg = (
                    "Sprawdź strukturę klasy i mapowanie ścieżki HTTP."
                    if lang == "pl"
                    else "Check class structure and HTTP path mapping."
                )
            findings.append(
                {
                    "severity": item.get("severity")
                    if item.get("severity") in ("error", "warning", "info")
                    else "info",
                    "message": msg,
                    "socratic_question": item.get("socratic_question"),
                    "file": item.get("file"),
                    "line": item.get("line"),
                }
            )
        conversation.touch()
        return {
            "conversation_id": conversation_id,
            "findings": findings,
            "suggested_next_step": data.get("suggested_next_step"),
        }
