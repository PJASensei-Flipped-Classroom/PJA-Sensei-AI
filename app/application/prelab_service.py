import re
from typing import List, Dict, Any

from app.application.dto import (
    PrelabStatusResponse,
    PrelabSubmitRequest,
    PrelabQuestionDTO,
    PrelabSubmitResponse,
)
from app.domain.conversation import Conversation
from app.domain.ports import ConversationRepository


def _msg(language: str, pl: str, en: str) -> str:
    return pl if language == "pl" else en


def _keyword_hit(keyword: str, answer: str) -> bool:
    kw = keyword.strip().lower()
    if not kw:
        return False
    # Word-boundary match; escape regex metacharacters in keywords.
    return re.search(rf"\b{re.escape(kw)}\b", answer, flags=re.IGNORECASE) is not None


class PrelabService:
    def __init__(self, repo: ConversationRepository):
        self.repo = repo

    def get_status(self, conv: Conversation) -> PrelabStatusResponse:
        # OLD getattr/legacy path (kept for reference):
        # prelab_cfg = getattr(conv.config, "pre_lab", None) or getattr(conv.config, "preLab", None)
        # enabled = bool(prelab_cfg and getattr(prelab_cfg, "enabled", False))
        # ... SingleQuestion / camelCase expectedKeywords fallbacks ...
        prelab_cfg = conv.config.pre_lab
        enabled = bool(prelab_cfg.enabled)

        questions: List[PrelabQuestionDTO] = []
        hint_after_fail = None

        if enabled:
            hint_after_fail = prelab_cfg.hint_after_fail
            for q in prelab_cfg.questions:
                questions.append(
                    PrelabQuestionDTO(
                        id=q.id,
                        question=q.question,
                        hint=None,
                    )
                )

        max_attempts = prelab_cfg.max_attempts if enabled else 2
        attempts = conv.prelab_attempts
        remaining_attempts = max(0, max_attempts - attempts) if max_attempts else None
        show_hint = attempts > 0

        return PrelabStatusResponse(
            enabled=enabled,
            passed=conv.prelab_completed,
            completed=conv.prelab_completed,
            questions=questions,
            attempts=attempts,
            max_attempts=max_attempts,
            remaining_attempts=remaining_attempts,
            hint_after_fail=hint_after_fail if show_hint else None,
        )

    def submit(self, conv: Conversation, req: PrelabSubmitRequest) -> Dict[str, Any]:
        # OLD: getattr(conv.config, "pre_lab", None) or getattr(conv.config, "preLab", None)
        prelab_cfg = conv.config.pre_lab
        enabled = bool(prelab_cfg.enabled)
        lang = conv.config.language

        if not enabled:
            conv.prelab_completed = True
            self.repo.save(conv)
            response = PrelabSubmitResponse(
                passed=True,
                unlocked=True,
                failed_ids=[],
                attempts=conv.prelab_attempts,
                remaining_attempts=None,
                feedback=_msg(lang, "Pre-Lab nie jest wymagany.", "Pre-Lab is not required."),
                prelab_completed=True,
            )
            return response.model_dump()

        max_attempts = prelab_cfg.max_attempts
        attempts = conv.prelab_attempts

        if attempts >= max_attempts:
            exhausted = _msg(lang, "Wyczerpano limit prób.", "Attempt limit exhausted.")
            response = PrelabSubmitResponse(
                passed=False,
                unlocked=False,
                failed_ids=[],
                attempts=attempts,
                remaining_attempts=0,
                feedback=exhausted,
                prelab_completed=False,
            )
            payload = response.model_dump()
            payload["detail"] = exhausted
            return payload

        conv.prelab_attempts = attempts + 1

        # OLD legacy single-question shape:
        # cfg_questions = getattr(prelab_cfg, "questions", [])
        # if not cfg_questions and getattr(prelab_cfg, "question", None):
        #     class SingleQuestion: ...
        #     cfg_questions = [SingleQuestion()]
        cfg_questions = list(prelab_cfg.questions)

        answers_dict: Dict[str, str] = {
            a.id: a.answer.strip().lower() for a in req.answers
        }

        failed_ids: List[str] = []

        for q in cfg_questions:
            q_id = q.id
            user_answer = answers_dict.get(q_id, "")
            # OLD: expected = getattr(q, "expected_keywords", []) or getattr(q, "expectedKeywords", [])
            expected = q.expected_keywords

            if not expected:
                if not user_answer:
                    failed_ids.append(q_id)
                continue

            # OLD: substring match (e.g. "Rest" inside "Forest")
            # has_match = any(str(kw).strip().lower() in user_answer for kw in expected)
            # Why: students could pass prelab with unrelated words that merely contain the keyword.
            # Wrong: `kw in answer` is substring, not token match.
            # Better: word-boundary regex (`_keyword_hit`) so "Forest" ≠ "Rest".
            has_match = any(_keyword_hit(str(kw), user_answer) for kw in expected)
            if not has_match:
                failed_ids.append(q_id)

        passed = len(failed_ids) == 0
        remaining = max(0, max_attempts - conv.prelab_attempts) if max_attempts else None

        if passed:
            conv.prelab_completed = True
            feedback = _msg(
                lang,
                "Gratulacje! Odpowiedzi poprawne, czat został odblokowany.",
                "Congratulations! Answers are correct; chat is unlocked.",
            )
        else:
            hint = prelab_cfg.hint_after_fail
            if lang == "pl":
                feedback = (
                    f"Niepoprawne odpowiedzi dla pytań: {', '.join(failed_ids)}."
                    + (f" Wskazówka: {hint}" if hint else "")
                )
            else:
                feedback = (
                    f"Incorrect answers for questions: {', '.join(failed_ids)}."
                    + (f" Hint: {hint}" if hint else "")
                )

        self.repo.save(conv)

        response = PrelabSubmitResponse(
            passed=passed,
            unlocked=passed,
            failed_ids=failed_ids,
            attempts=conv.prelab_attempts,
            remaining_attempts=remaining,
            feedback=feedback,
            prelab_completed=conv.prelab_completed,
        )
        return response.model_dump()
