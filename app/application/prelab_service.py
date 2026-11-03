from typing import List, Dict, Any, Optional

from app.application.dto import (
    PrelabStatusResponse,
    PrelabSubmitRequest,
    PrelabQuestionDTO,
)
from app.domain.conversation import Conversation
from app.domain.ports import ConversationRepository


class PrelabService:
    def __init__(self, repo: ConversationRepository):
        self.repo = repo

    def get_status(self, conv: Conversation) -> PrelabStatusResponse:
        prelab_cfg = getattr(conv.config, "pre_lab", None) or getattr(conv.config, "preLab", None)
        enabled = bool(prelab_cfg and getattr(prelab_cfg, "enabled", False))

        questions: List[PrelabQuestionDTO] = []
        hint_after_fail = None

        if enabled and prelab_cfg:
            hint_after_fail = getattr(prelab_cfg, "hint_after_fail", None)

            cfg_questions = getattr(prelab_cfg, "questions", [])
            if cfg_questions:
                for q in cfg_questions:
                    questions.append(
                        PrelabQuestionDTO(
                            id=getattr(q, "id", "q1"),
                            question=getattr(q, "question", ""),
                            hint=getattr(q, "hint", None),
                        )
                    )
            elif getattr(prelab_cfg, "question", None):
                questions.append(
                    PrelabQuestionDTO(
                        id="q1",
                        question=getattr(prelab_cfg, "question", ""),
                        hint=hint_after_fail,
                    )
                )

        max_attempts = getattr(prelab_cfg, "max_attempts", 2) if prelab_cfg else 2
        attempts = getattr(conv, "prelab_attempts", 0)
        remaining_attempts = max(0, max_attempts - attempts) if max_attempts else None
        show_hint = attempts > 0

        return PrelabStatusResponse(
            enabled=enabled,
            passed=getattr(conv, "prelab_completed", False),
            completed=getattr(conv, "prelab_completed", False),
            questions=questions,
            attempts=attempts,
            max_attempts=max_attempts,
            remaining_attempts=remaining_attempts,
            hint_after_fail=hint_after_fail if show_hint else None,
        )

    def submit(self, conv: Conversation, req: PrelabSubmitRequest) -> Dict[str, Any]:
        prelab_cfg = getattr(conv.config, "pre_lab", None) or getattr(conv.config, "preLab", None)
        enabled = bool(prelab_cfg and getattr(prelab_cfg, "enabled", False))

        if not enabled:
            conv.prelab_completed = True
            self.repo.save(conv)
            return {
                "passed": True,
                "unlocked": True,
                "failed_ids": [],
                "attempts": getattr(conv, "prelab_attempts", 0),
                "remaining_attempts": None,
                "feedback": "Pre-Lab nie jest wymagany.",
                "prelab_completed": True,
            }

        max_attempts = getattr(prelab_cfg, "max_attempts", 2) if prelab_cfg else 2
        attempts = getattr(conv, "prelab_attempts", 0)

        if attempts >= max_attempts:
            return {
                "passed": False,
                "unlocked": False,
                "failed_ids": [],
                "attempts": attempts,
                "remaining_attempts": 0,
                "feedback": "Wyczerpano limit prób.",
                "detail": "Wyczerpano limit prób.",
                "prelab_completed": False,
            }

        conv.prelab_attempts = attempts + 1

        cfg_questions = getattr(prelab_cfg, "questions", [])
        if not cfg_questions and getattr(prelab_cfg, "question", None):
            class SingleQuestion:
                id = "q1"
                question = getattr(prelab_cfg, "question")
                expected_keywords = getattr(prelab_cfg, "expected_keywords", []) or getattr(
                    prelab_cfg, "expectedKeywords", []
                )

            cfg_questions = [SingleQuestion()]

        answers_dict: Dict[str, str] = {
            a.id: a.answer.strip().lower() for a in req.answers
        }

        failed_ids: List[str] = []

        for q in cfg_questions:
            q_id = getattr(q, "id", "q1")
            user_answer = answers_dict.get(q_id, "")

            expected = getattr(q, "expected_keywords", []) or getattr(
                q, "expectedKeywords", []
            )

            if not expected:
                if not user_answer:
                    failed_ids.append(q_id)
                continue

            has_match = any(str(kw).strip().lower() in user_answer for kw in expected)
            if not has_match:
                failed_ids.append(q_id)

        passed = len(failed_ids) == 0
        remaining = max(0, max_attempts - conv.prelab_attempts) if max_attempts else None

        if passed:
            conv.prelab_completed = True
            feedback = "Gratulacje! Odpowiedzi poprawne, czat został odblokowany."
        else:
            hint = getattr(prelab_cfg, "hint_after_fail", None)
            feedback = (
                f"Niepoprawne odpowiedzi dla pytań: {', '.join(failed_ids)}."
                + (f" Wskazówka: {hint}" if hint else "")
            )

        self.repo.save(conv)

        return {
            "passed": passed,
            "unlocked": passed,
            "failed_ids": failed_ids,
            "attempts": conv.prelab_attempts,
            "remaining_attempts": remaining,
            "feedback": feedback,
            "prelab_completed": conv.prelab_completed,
        }