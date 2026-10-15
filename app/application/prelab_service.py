import re
from typing import Dict
from app.domain.conversation import Conversation
from app.domain.ports import ConversationRepository
from app.application.dto import (
    PrelabStatusResponse, PrelabQuestionDTO,
    PrelabSubmitRequest, PrelabSubmitResponse
)


class PrelabService:
    def __init__(self, repo: ConversationRepository):
        self.repo = repo

    def get_status(self, conv: Conversation) -> PrelabStatusResponse:
        config = conv.config.pre_lab
        questions_dto = [PrelabQuestionDTO(id=q.id, question=q.question) for q in config.questions]
        score = len(config.questions) if conv.prelab_completed else 0

        show_hint = (conv.prelab_attempts >= config.max_attempts) and not conv.prelab_completed

        return PrelabStatusResponse(
            enabled=config.enabled,
            passed=conv.prelab_completed,
            questions=questions_dto,
            attempts=conv.prelab_attempts,
            max_attempts=config.max_attempts,
            score=score,
            hint_after_fail=config.hint_after_fail if show_hint else None
        )

    def submit(self, conv: Conversation, req: PrelabSubmitRequest) -> PrelabSubmitResponse:
        config = conv.config.pre_lab

        if not config.enabled or conv.prelab_completed:
            return PrelabSubmitResponse(
                passed=True, score=len(config.questions), detail="Zaliczone automatycznie lub już zdane.",
                failed_ids=[], attempts=conv.prelab_attempts, unlocked=True
            )

        if conv.prelab_attempts >= config.max_attempts:
            return PrelabSubmitResponse(
                passed=False, score=0, detail="Wyczerpano limit prób.",
                failed_ids=[q.id for q in config.questions], attempts=conv.prelab_attempts, unlocked=False
            )

        conv.prelab_attempts += 1
        answers_dict = {a.id: a.answer.strip() for a in req.answers}
        failed_ids = []
        score = 0

        for q in config.questions:
            ans = answers_dict.get(q.id, "")

            if not ans:
                failed_ids.append(q.id)
                continue

            if not q.expected_keywords:
                score += 1
                continue

            passed_q = True
            for kw in q.expected_keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if not re.search(pattern, ans, re.IGNORECASE):
                    passed_q = False
                    break

            if passed_q:
                score += 1
            else:
                failed_ids.append(q.id)

        passed = len(failed_ids) == 0
        if passed:
            conv.prelab_completed = True

        self.repo.save(conv)

        if passed:
            detail = "Pre-lab zaliczony!"
        elif conv.prelab_attempts >= config.max_attempts:
            detail = f"Nie zaliczono. {config.hint_after_fail or 'Koniec prób.'}"
        else:
            detail = "Błędne odpowiedzi, spróbuj ponownie."

        return PrelabSubmitResponse(
            passed=passed,
            score=score,
            detail=detail,
            failed_ids=failed_ids,
            attempts=conv.prelab_attempts,
            unlocked=passed
        )