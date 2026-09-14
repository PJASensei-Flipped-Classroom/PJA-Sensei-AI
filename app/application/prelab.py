"""Ewaluacja quizu pre-lab: odblokowanie czatu po zaliczeniu lub wyczerpaniu prób."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.application.dto import PreLabSubmitRequest
from app.application.sessions import SessionService
from app.domain.conversation import Conversation


@dataclass(frozen=True)
class PreLabEvaluationResult:
    """Wynik oceny quizu wstępnego przekazywany do warstwy API."""

    passed: bool
    score: float
    detail: str
    failed_ids: list[str]
    attempts: int
    max_attempts: int | None
    hint_after_fail: str | None

    def to_dict(self) -> dict[str, Any]:
        """Mapuje wynik na payload odpowiedzi HTTP (z aliasami feedback/unlocked)."""
        return {
            "passed": self.passed,
            "score": self.score,
            "detail": self.detail,
            "feedback": self.detail,
            "unlocked": self.passed,
            "failed_ids": self.failed_ids,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "hint_after_fail": self.hint_after_fail,
        }


class PrelabService:
    """Serwis weryfikacji i ewaluacji przygotowania wstępnego studenta."""

    def __init__(self, sessions: SessionService) -> None:
        self._sessions = sessions

    def get_prelab_public(self, conversation_id: str) -> dict[str, Any]:
        """Zwraca publiczne pytania bez ujawniania klucza odpowiedzi."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        prelab = getattr(conversation.config, "pre_lab", None) or getattr(conversation.config, "preLab", None)

        if not prelab or not getattr(prelab, "enabled", False):
            return {
                "enabled": False,
                "passed": True,
                "questions": [],
                "attempts": 0,
                "max_attempts": None,
                "score": 1.0,
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

    @staticmethod
    def _is_keyword_present(keyword: str, text: str) -> bool:
        """Sprawdza obecność słowa kluczowego z poszanowaniem granic wyrazów."""
        pattern = rf"\b{re.escape(keyword.lower())}\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _evaluate_question(self, question: Any, student_answer: str) -> bool:
        """Ocenia pojedyncze pytanie quizowe."""
        cleaned = student_answer.strip()
        if not question.expected_keywords:
            return bool(cleaned)

        return any(self._is_keyword_present(kw, cleaned) for kw in question.expected_keywords)

    def submit_prelab(self, conversation_id: str, payload: PreLabSubmitRequest) -> dict[str, Any]:
        """Weryfikuje nadesłane odpowiedzi i aktualizuje uprawnienia sesji."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        prelab = getattr(conversation.config, "pre_lab", None) or getattr(conversation.config, "preLab", None)

        if not prelab or not getattr(prelab, "enabled", False):
            conversation.prelab_passed = True
            self._sessions.save_conversation(conversation_id, conversation)
            return {
                "passed": True,
                "detail": "Pre-lab not required",
                "feedback": "Pre-lab not required",
                "score": 1.0,
                "unlocked": True,
            }

        # Blokada po przekroczeniu liczby prób
        if (
            prelab.max_attempts is not None
            and conversation.prelab_attempts >= prelab.max_attempts
            and not conversation.prelab_passed
        ):
            return PreLabEvaluationResult(
                passed=False,
                score=conversation.last_prelab_score or 0.0,
                detail="Maksymalna liczba prób została wyczerpana.",
                failed_ids=[],
                attempts=conversation.prelab_attempts,
                max_attempts=prelab.max_attempts,
                hint_after_fail=prelab.hint_after_fail,
            ).to_dict()

        conversation.prelab_attempts += 1
        answers_by_id = {a.id: a.answer for a in payload.answers}
        failures: list[str] = []
        matched = 0
        total = len(prelab.questions) or 1

        for q in prelab.questions:
            student_ans = answers_by_id.get(q.id, "")
            if self._evaluate_question(q, student_ans):
                matched += 1
            else:
                failures.append(q.id)

        score = round(matched / total, 3)
        conversation.last_prelab_score = score
        conversation.prelab_passed = len(failures) == 0
        conversation.touch()
        self._sessions.save_conversation(conversation_id, conversation)

        return PreLabEvaluationResult(
            passed=conversation.prelab_passed,
            score=score,
            detail="Quiz zaliczony pomyślnie." if conversation.prelab_passed else f"Błędne pytania: {', '.join(failures)}",
            failed_ids=failures,
            attempts=conversation.prelab_attempts,
            max_attempts=prelab.max_attempts,
            hint_after_fail=None if conversation.prelab_passed else prelab.hint_after_fail,
        ).to_dict()