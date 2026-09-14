"""Generowanie podsumowania sesji laboratoryjnej (LLM + metryki IDE / reveal)."""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any

from app.application.response_pipeline import compress_history
from app.application.sessions import SessionService
from app.domain.conversation import Conversation
from app.ports import LlmPort

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES_FOR_SUMMARY = 24


class SummaryService:
    """Serwis odpowiedzialny za syntetyczną ocenę dydaktyczną sesji laboratoryjnej."""

    def __init__(self, sessions: SessionService, llm: LlmPort) -> None:
        self._sessions = sessions
        self._llm = llm

    @staticmethod
    def _structured_ide_events(conversation: Conversation) -> dict[str, Any]:
        """Agreguje statystyki zdarzeń z edytora kodu wraz z próbkowaniem."""
        counts: Counter[str] = Counter()
        samples: list[dict[str, Any]] = []

        for e in conversation.ide_events:
            etype = str(e.get("type") or "unknown")
            counts[etype] += 1
            if len(samples) < 12:
                samples.append({
                    "type": etype,
                    "meta": e.get("meta") or {},
                    "at": e.get("at"),
                })

        return {
            "counts": dict(counts),
            "copy_blocked": counts.get("copy_blocked", 0),
            "paste_attempt": counts.get("paste_attempt", 0),
            "file_opened": counts.get("file_opened", 0),
            "reveals": conversation.reveal_count,
            "total_events": len(conversation.ide_events),
            "recent": samples,
        }

    def _format_conversation_history(self, conversation: Conversation) -> str:
        """Przygotowuje skondensowaną historię konwersacji chroniąc okno kontekstowe."""
        messages_to_process = [
            {"role": m["role"], "content": m["content"]}
            for m in conversation.messages
            if m.get("role") in ("user", "assistant")
        ]
        compressed = compress_history(
            messages_to_process,
            language=conversation.config.language,
            max_length=MAX_HISTORY_MESSAGES_FOR_SUMMARY,
        )
        return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in compressed)

    async def generate_summary(self, conversation_id: str) -> dict[str, Any]:
        """Generuje raport z przebiegu laboratorium dla prowadzącego zajęcia."""
        conversation = self._sessions.get_conversation_or_404(conversation_id)
        conversation.touch()

        scores = conversation.prompt_scores
        avg_score = sum(scores) / len(scores) if scores else 0.0
        lang = conversation.config.language
        is_en = lang == "en"

        goals = conversation.config.learning_context.goals or []
        goal_progress = conversation.goal_progress or []
        criteria = conversation.config.evaluation_criteria or []
        events_structured = self._structured_ide_events(conversation)

        events_summary = {
            "copy_blocked": events_structured["copy_blocked"],
            "paste_attempt": events_structured["paste_attempt"],
            "file_opened": events_structured["file_opened"],
            "reveals": conversation.reveal_count,
        }

        feedbacks = [
            f"rating={m['student_feedback']['rating']}, comment={m['student_feedback'].get('comment', '')}"
            for m in conversation.messages
            if m.get("role") == "assistant" and "student_feedback" in m
        ]

        history_text = self._format_conversation_history(conversation)
        goals_text = "\n".join(f"- {g}" for g in goals) if goals else "- (brak zdefiniowanych)"
        progress_text = (
            "\n".join(f"- {g.get('goal')}: {g.get('status')}" for g in goal_progress)
            if goal_progress
            else "brak"
        )
        criteria_text = (
            "\n".join(f"- {c}" for c in criteria)
            if criteria
            else "- Samodzielność, precyzja pytań, zrozumienie kodu"
        )
        feedbacks_text = "\n".join(feedbacks) if feedbacks else "brak"

        prompt = (
            f"Summarize student work for lecturer.\n"
            f"Language: {'English' if is_en else 'Polish'}.\n"
            f"Assignment: {conversation.problem}\n\n"
            f"Learning goals:\n{goals_text}\n\n"
            f"Observed goal progress:\n{progress_text}\n\n"
            f"Evaluation criteria:\n{criteria_text}\n\n"
            f"Conversation snippet:\n{history_text}\n\n"
            f"Prompt scores: {scores} (average: {avg_score:.2f})\n"
            f"Student feedbacks: {feedbacks_text}\n"
            f"Hints revealed: {conversation.reveal_count}\n"
            f"IDE events summary: {json.dumps(events_structured, ensure_ascii=False)}\n\n"
            "Return JSON with keys:\n"
            "- mastery_score (integer 0-100)\n"
            '- goal_mastery: [{"goal":"...","status":"not_started|in_progress|done","notes":"..."}]\n'
            '- criteria_assessment: [{"criterion":"...","assessment":"..."}]\n'
            '- reveal_usage: {"count": N, "notes": "..."}\n'
            "- ide_events_detail: string\n"
            "- student_actions: string\n"
            "- agent_evaluation_of_student: string\n"
            "- student_evaluation_of_agent: string\n"
            "- professors_summary: string"
        )

        try:
            response = await self._llm.create_chat_completion(
                model=self._llm.model_for(conversation),
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000,
            )
            raw = response.choices[0].message.content or "{}"
            summary = json.loads(raw)
        except Exception as exc:
            logger.error("Błąd generowania podsumowania LLM dla sesji %s: %s", conversation_id, exc)
            fallback_msg = (
                "Automatic summary could not be generated due to a temporary service issue."
                if is_en
                else "Nie udało się wygenerować automatycznego podsumowania z powodu błędu usługi."
            )
            summary = {
                "mastery_score": 0,
                "student_actions": "",
                "agent_evaluation_of_student": "",
                "student_evaluation_of_agent": "",
                "professors_summary": fallback_msg,
                "goal_mastery": [{"goal": g, "status": "not_started", "notes": ""} for g in goals],
                "criteria_assessment": [{"criterion": c, "assessment": ""} for c in criteria],
                "reveal_usage": {"count": conversation.reveal_count, "notes": ""},
                "ide_events_detail": "",
            }

        conversation.summary_generated = True

        # Gwarancja obecności twardych, zweryfikowanych metryk programistycznych
        summary["ide_events"] = events_summary
        summary["ide_events_structured"] = events_structured
        summary["goals"] = list(goals)
        summary["goal_progress"] = list(goal_progress)
        summary["evaluation_criteria"] = list(criteria)
        summary["reveal_count"] = conversation.reveal_count

        if not isinstance(summary.get("reveal_usage"), dict):
            summary["reveal_usage"] = {
                "count": conversation.reveal_count,
                "notes": str(summary.get("reveal_usage") or ""),
            }
        else:
            summary["reveal_usage"].setdefault("count", conversation.reveal_count)

        conversation.last_summary = summary
        self._sessions.save_conversation(conversation_id, conversation)
        return summary