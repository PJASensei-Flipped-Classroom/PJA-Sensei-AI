from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.api.schemas.requests import PreLabSubmitRequest
from app.domain.sensei import PreLabConfig, PreLabQuestion

if TYPE_CHECKING:
    from app.application.container import AppContainer


class PrelabService:
    def __init__(self, app: AppContainer) -> None:
        self._app = app

    def get_prelab_public(self, conversation_id: str) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        prelab = conversation.config.preLab
        if not prelab or not prelab.enabled:
            return {
                "enabled": False,
                "passed": True,
                "questions": [],
                "attempts": 0,
                "max_attempts": None,
                "score": None,
            }
        return {
            "enabled": True,
            "passed": conversation.prelab_passed,
            "questions": [{"id": q.id, "prompt": q.prompt} for q in prelab.questions],
            "attempts": conversation.prelab_attempts,
            "max_attempts": prelab.max_attempts,
            "score": conversation.last_prelab_score,
            "hint_after_fail": prelab.hint_after_fail,
        }

    def submit_prelab(self, conversation_id: str, payload: PreLabSubmitRequest) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        prelab = conversation.config.preLab
        if not prelab or not prelab.enabled:
            conversation.prelab_passed = True
            return {"passed": True, "detail": "Pre-lab not required", "score": 1.0}

        if (
            prelab.max_attempts is not None
            and conversation.prelab_attempts >= prelab.max_attempts
            and not conversation.prelab_passed
        ):
            return {
                "passed": False,
                "detail": "max_attempts exceeded",
                "failed_ids": [],
                "score": conversation.last_prelab_score or 0.0,
                "attempts": conversation.prelab_attempts,
                "max_attempts": prelab.max_attempts,
                "hint_after_fail": prelab.hint_after_fail,
            }

        conversation.prelab_attempts += 1
        answers_by_id = {a.id: a.answer.lower() for a in payload.answers}
        failures: list[str] = []
        matched = 0
        total = len(prelab.questions) or 1
        for q in prelab.questions:
            student_ans = answers_by_id.get(q.id, "")
            if not q.expected_keywords:
                ok = bool(student_ans.strip())
            else:
                ok = any(kw.lower() in student_ans for kw in q.expected_keywords)
            if ok:
                matched += 1
            else:
                failures.append(q.id)

        score = round(matched / total, 3)
        conversation.last_prelab_score = score
        conversation.prelab_passed = len(failures) == 0
        conversation.touch()
        return {
            "passed": conversation.prelab_passed,
            "detail": (
                "OK"
                if conversation.prelab_passed
                else f"Failed questions: {', '.join(failures)}"
            ),
            "failed_ids": failures,
            "score": score,
            "attempts": conversation.prelab_attempts,
            "max_attempts": prelab.max_attempts,
            "hint_after_fail": (
                None if conversation.prelab_passed else prelab.hint_after_fail
            ),
        }

    async def generate_prelab(self, conversation_id: str) -> dict:
        conversation = self._app.sessions.get_conversation_or_404(conversation_id)
        rag_text, _ = self._app.rag.retrieve_context(
            conversation_id, conversation.problem
        )
        materials = "\n".join(
            f"- {m.title}: {m.url}"
            for m in conversation.config.learningContext.referenceMaterials
        )
        lang = conversation.config.language
        prompt = f"""
Generate exactly 3 short pre-lab quiz questions for students before coding.
Assignment: {conversation.problem}
Materials:
{materials}
RAG excerpts:
{rag_text[:2500]}

Return JSON:
{{
  "questions": [
    {{"id": "q1", "prompt": "...", "expected_keywords": ["kw1", "kw2"]}}
  ]
}}
Language of prompts: {"English" if lang == "en" else "Polish"}.
"""
        response = await self._app.client.chat.completions.create(
            model=self._app.llm.model_for(conversation),
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"questions": []}
        questions = data.get("questions") or []
        parsed = []
        for i, q in enumerate(questions[:3], start=1):
            parsed.append(
                PreLabQuestion(
                    id=str(q.get("id") or f"q{i}"),
                    prompt=str(q.get("prompt") or ""),
                    expected_keywords=list(q.get("expected_keywords") or []),
                )
            )
        conversation.config.preLab = PreLabConfig(enabled=True, questions=parsed)
        conversation.prelab_passed = False
        conversation.touch()
        return self.get_prelab_public(conversation_id)
