"""Ewaluacja quizu pre-lab: weryfikacja odpowiedzi i odblokowanie czatu po zaliczeniu."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
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
        """Konwertuje wynik na słownik odpowiedzi HTTP ze zduplikowanymi polami kontraktu."""
        data = asdict(self)
        data["feedback"] = self.detail
        data["unlocked"] = self.passed
        return data


class PrelabService:
    """Serwis weryfikacji i oceny przygotowania wstępnego studenta."""

    def __init__(self, sessions: SessionService) -> None:
        self._sessions = sessions

    @staticmethod
    def _extract_prelab_config(conversation: Conversation) -> Any | None:
        """Pobiera konfigurację pre-labu niezależnie od konwencji nazewnictwa (snake_case vs camelCase)."""
        cfg = conversation.config
        return getattr(cfg, "pre_lab", None) or getattr(cfg, "preLab", None)

    def get_prelab_public(self, conversation_id: str) -> dict[str, Any]:
        """Zwraca pytania quizowe widoczne dla studenta bez ujawniania słów kluczowych."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        prelab = self._extract_prelab_config(conversation)

        # Jeśli pre-lab jest wyłączony lub nieobecny, oznaczamy go jako domyślnie zaliczony
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
            "questions": [{"id": q.id, "question": q.prompt} for q in prelab.questions],
            "attempts": conversation.prelab_attempts,
            "max_attempts": prelab.max_attempts,
            "score": conversation.last_prelab_score,
            "hint_after_fail": prelab.hint_after_fail,
        }

    @staticmethod
    def _is_keyword_present(keyword: str, text: str) -> bool:
        """Sprawdza obecność słowa kluczowego z poszanowaniem granic słów (\b)."""
        pattern = rf"\b{re.escape(keyword.lower())}\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _evaluate_question(self, question: Any, student_answer: str) -> bool:
        """Ocenia odpowiedź na pojedyncze pytanie na podstawie listy expected_keywords."""
        cleaned_answer = student_answer.strip()
        expected_keywords = getattr(question, "expected_keywords", None) or []

        # Pytanie otwarte bez zdefiniowanych słów kluczowych: akceptuje każdą niepustą odpowiedź
        if not expected_keywords:
            return bool(cleaned_answer)

        return any(self._is_keyword_present(kw, cleaned_answer) for kw in expected_keywords)

    def submit_prelab(self, conversation_id: str, payload: PreLabSubmitRequest) -> dict[str, Any]:
        """Weryfikuje nadesłane odpowiedzi, nalicza próbę i odblokowuje dostęp do czatu po zaliczeniu."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        prelab = self._extract_prelab_config(conversation)

        # Scenariusz 1: Pre-lab nie jest wymagany w konfiguracji tego zadania
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

        # Scenariusz 2: Blokada po wyczerpaniu limitu podejść
        has_max_attempts = prelab.max_attempts is not None
        if has_max_attempts and conversation.prelab_attempts >= prelab.max_attempts and not conversation.prelab_passed:
            return PreLabEvaluationResult(
                passed=False,
                score=conversation.last_prelab_score or 0.0,
                detail="Maksymalna liczba prób została wyczerpana.",
                failed_ids=[],
                attempts=conversation.prelab_attempts,
                max_attempts=prelab.max_attempts,
                hint_after_fail=prelab.hint_after_fail,
            ).to_dict()

        # Scenariusz 3: Ocena nadesłanych odpowiedzi
        conversation.prelab_attempts += 1
        answers_by_id = {item.id: item.answer for item in payload.answers}

        failed_question_ids: list[str] = []
        correct_count = 0
        total_questions = len(prelab.questions) or 1

        for question in prelab.questions:
            student_answer = answers_by_id.get(question.id, "")
            if self._evaluate_question(question, student_answer):
                correct_count += 1
            else:
                failed_question_ids.append(question.id)

        is_passed = len(failed_question_ids) == 0
        score = round(correct_count / total_questions, 3)

        # Aktualizacja agregatu rozmowy
        conversation.last_prelab_score = score
        conversation.prelab_passed = is_passed
        conversation.touch()
        self._sessions.save_conversation(conversation_id, conversation)

        status_detail = (
            "Quiz zaliczony pomyślnie."
            if is_passed
            else f"Błędne pytania: {', '.join(failed_question_ids)}"
        )

        return PreLabEvaluationResult(
            passed=is_passed,
            score=score,
            detail=status_detail,
            failed_ids=failed_question_ids,
            attempts=conversation.prelab_attempts,
            max_attempts=prelab.max_attempts,
            hint_after_fail=None if is_passed else prelab.hint_after_fail,
        ).to_dict()