import uuid
import time
from typing import Optional, List, Dict, Any, Union, Tuple

from app.application.dto import GoalProgressEntryDTO, SessionSummaryResponse, RagPreviewDTO, RagMaterialPreviewDTO
from app.application.grade_payload import build_grade_sync_payload
from app.domain.conversation import Conversation, GoalStatus
from app.domain.ports import ConversationRepository, RagPort, WebhookPort
from app.domain.sensei import SenseiConfig
from app.domain.exceptions import UnknownConversation, PrelabRequired
from app.core.config import settings


class SessionService:
    def __init__(self, repo: ConversationRepository, rag: Optional[RagPort] = None, webhooks: Optional[WebhookPort] = None):
        self.repo = repo
        self.rag = rag
        self.webhooks = webhooks

    def start_conversation(
        self,
        config: Union[SenseiConfig, Dict[str, Any]],
        *,
        owner_sub: Optional[str] = None,
        lab_id: Optional[str] = None,
    ) -> Tuple[Conversation, RagPreviewDTO]:
        if isinstance(config, dict):
            config = SenseiConfig(**config)

        conv_id = str(uuid.uuid4())
        goal_progress: Dict[str, GoalStatus] = {
            goal.id: "not_started" for goal in config.learning_context.goals
        }
        # OLD:
        # conv = Conversation(
        #     id=conv_id,
        #     config=config,
        #     goal_progress=goal_progress,
        #     prelab_completed=not config.pre_lab.enabled
        # )
        # Why: JWT-backed deploys need session ownership binding.
        # Wrong: any valid token could use any known conversation_id (no owner_sub).
        # Better: persist owner_sub/lab_id from JWT claims at create time for access checks.
        conv = Conversation(
            id=conv_id,
            config=config,
            goal_progress=goal_progress,
            prelab_completed=not config.pre_lab.enabled,
            owner_sub=owner_sub,
            lab_id=lab_id,
        )
        chunks = 0
        if self.rag is not None and config.reference_materials:
            chunks = self.rag.ingest(conv_id, config.reference_materials)

        self.repo.save(conv)
        preview = RagPreviewDTO(
            chunks_ingested=chunks,
            materials=[
                RagMaterialPreviewDTO(title=m.title, link=m.link)
                for m in config.reference_materials
            ],
        )
        return conv, preview

    # OLD: unused helper that leaked repo._store (port bypass)
    # def list_conversations(self) -> List[Dict[str, Any]]:
    #     all_convs = getattr(self.repo, "_store", {}).values()
    #     ...

    def list_conversations(self) -> List[Dict[str, Any]]:
        return [
            {
                "conversation_id": c.id,
                "language": c.config.language,
                "lab_score": c.calculate_lab_score(),
                "messages_count": len(c.messages),
                "tokens_used": c.token_usage,
                "prelab_completed": c.prelab_completed,
                "hints_revealed": c.hints_revealed,
                "frustration_streak": c.frustration_streak,
                "goals_done": sum(1 for s in c.goal_progress.values() if s == "done"),
                "goals_total": len(c.config.learning_context.goals),
            }
            for c in self.repo.list_active()
        ]

    def count_active(self) -> int:
        return self.repo.count_active()

    def get_or_404(self, conv_id: str) -> Conversation:
        conv = self.repo.get(conv_id)
        if not conv or getattr(conv, "is_deleted", False):
            raise UnknownConversation(f"Conversation {conv_id} not found")
        conv.touch()
        self.repo.save(conv)
        return conv

    def delete(self, conv_id: str) -> Dict[str, Any]:
        conv = self.get_or_404(conv_id)
        summary_dict = self._build_and_store_summary(conv)

        rag_cleaned = False
        if self.rag is not None:
            self.rag.delete_conversation(conv_id)
            rag_cleaned = True
        # OLD: always reported "rag_cleaned": True even when rag was None

        conv.is_deleted = True
        conv.deleted_at = time.time()
        self.repo.save(conv)

        return {
            "status": "deleted",
            "id": conv_id,
            "conversation_id": conv_id,
            "soft_deleted": True,
            "rag_cleaned": rag_cleaned,
            "summary": summary_dict,
        }

    def export(self, conv_id: str) -> dict:
        conv = self.get_or_404(conv_id)
        return conv.model_dump(by_alias=True)

    def record_event(self, conv_id: str, event_type: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        conv = self.get_or_404(conv_id)
        now = time.time()
        conv.events.append({
            "type": event_type,
            "meta": meta or {},
            "timestamp": now,
        })

        streak_incremented = False
        # OLD:
        # if event_type in ("test_failed", "compile_error", "build_failed", "runtime_error"):
        #     conv.frustration_streak += 1
        # elif event_type in ("test_passed", "goal_completed"):
        #     conv.frustration_streak = 0
        # Why: hint unlock is gated on frustration_streak; farming /events unlocked hints in seconds.
        # Wrong: every matching event incremented streak with no cooldown.
        # Better: increment at most once per FRUSTRATION_EVENT_COOLDOWN_SECONDS; still append the event.
        frustration_types = ("test_failed", "compile_error", "build_failed", "runtime_error")
        reset_types = ("test_passed", "goal_completed")
        if event_type in frustration_types:
            cooldown = float(settings.FRUSTRATION_EVENT_COOLDOWN_SECONDS)
            last = conv.last_frustration_at or 0.0
            if now - last >= cooldown:
                conv.frustration_streak += 1
                conv.last_frustration_at = now
                streak_incremented = True
            # Focus mode: soft tutoring window after real IDE failures.
            focus_secs = max(0, int(getattr(conv.config, "focus_mode_seconds", 0) or 0))
            if focus_secs > 0:
                conv.focus_until = now + focus_secs
        elif event_type in reset_types:
            conv.frustration_streak = 0

        self.repo.save(conv)

        if self.webhooks is not None:
            self.webhooks.send_event(
                "ide_event",
                {
                    "conversation_id": conv_id,
                    "event_type": event_type,
                    "meta": meta or {},
                    "frustration_streak": conv.frustration_streak,
                },
            )

        # OLD: return {
        #     "status": "recorded",
        #     "event_type": event_type,
        #     "frustration_streak": conv.frustration_streak,
        # }
        return {
            "status": "recorded",
            "event_type": event_type,
            "frustration_streak": conv.frustration_streak,
            "streak_incremented": streak_incremented,
            "focus_until": conv.focus_until,
            "in_focus_mode": conv.in_focus_mode(now),
        }

    def purge_old_sessions(self) -> int:
        return self.repo.purge_expired(settings.CONVERSATION_TTL_SECONDS)

    def ensure_prelab_passed(self, conv_id: str) -> Conversation:
        conv = self.get_or_404(conv_id)
        if conv.config.pre_lab.enabled and not conv.prelab_completed:
            raise PrelabRequired(conv.config.language)
        return conv

    def _build_and_store_summary(self, conv: Conversation) -> Dict[str, Any]:
        goal_entries = [
            GoalProgressEntryDTO(goal=g.id, status=conv.goal_progress.get(g.id, "not_started"))
            for g in conv.config.learning_context.goals
        ]
        done_goals = [g.description for g in conv.config.learning_context.goals if conv.goal_progress.get(g.id) == "done"]
        pending_goals = [g.description for g in conv.config.learning_context.goals if conv.goal_progress.get(g.id) != "done"]
        lab_score = conv.calculate_lab_score()

        if conv.config.language == "pl":
            # OLD: f"... wynik {lab_score}% ..."  # lab_score is 0–10, not a percent
            summary_text = (
                f"Podsumowanie sesji laboratoryjnej: wynik {lab_score}/10 "
                f"(ukończone cele: {len(done_goals)}/{len(goal_entries)}). "
            )
            if done_goals:
                summary_text += f"Zrealizowano: {', '.join(done_goals)}. "
            if pending_goals:
                summary_text += f"Do dopracowania: {', '.join(pending_goals)}."
        else:
            # OLD: f"... score {lab_score}% ..."
            summary_text = (
                f"Lab session summary: score {lab_score}/10 "
                f"(completed goals: {len(done_goals)}/{len(goal_entries)}). "
            )
            if done_goals:
                summary_text += f"Completed: {', '.join(done_goals)}. "
            if pending_goals:
                summary_text += f"Remaining: {', '.join(pending_goals)}."

        summary_dto = SessionSummaryResponse(
            conversation_id=conv.id,
            summary=summary_text.strip(),
            lab_score=lab_score,
            goal_progress=goal_entries,
            tokens_used=conv.token_usage,
            messages_count=len(conv.messages),
            hints_used=conv.hints_revealed,
            events_count=len(conv.events),
            completed=conv.all_goals_done(),
        )
        summary_dict = summary_dto.model_dump()
        conv.summary = summary_dict
        # Prepare Spring grade-sync envelope (stored + webhook; Spring will consume later).
        grade = build_grade_sync_payload(
            conv, trigger="session_summary", summary_text=summary_text.strip()
        )
        conv.grade_payload = grade
        self.repo.save(conv)

        if self.webhooks is not None:
            self.webhooks.send_event(
                "session_summary",
                {"conversation_id": conv.id, "summary": summary_dict},
            )
            self.webhooks.send_event("grade_sync_prepared", grade)
        summary_dict["grade_payload"] = grade
        return summary_dict

    def generate_summary(self, conv_id: str) -> Dict[str, Any]:
        conv = self.get_or_404(conv_id)
        return self._build_and_store_summary(conv)

    def add_intervention_note(
        self, conv_id: str, text: str, author_sub: Optional[str] = None
    ) -> Dict[str, Any]:
        conv = self.get_or_404(conv_id)
        note = {
            "text": text.strip(),
            "author_sub": author_sub,
            "timestamp": time.time(),
        }
        conv.intervention_notes.append(note)
        self.repo.save(conv)
        return {"status": "recorded", "notes_count": len(conv.intervention_notes), "note": note}

    def observe(self, conv_id: str) -> Dict[str, Any]:
        """Professor read-only snapshot (messages + notes + grade payload)."""
        conv = self.get_or_404(conv_id)
        return {
            "conversation_id": conv.id,
            "owner_sub": conv.owner_sub,
            "lab_id": conv.lab_id,
            "lab_score": conv.calculate_lab_score(),
            "goal_progress": conv.goal_progress,
            "hints_revealed": conv.hints_revealed,
            "highest_hint_level": conv.highest_hint_level,
            "frustration_streak": conv.frustration_streak,
            "focus_until": conv.focus_until,
            "in_focus_mode": conv.in_focus_mode(),
            "messages": [m.model_dump() for m in conv.messages],
            "intervention_notes": list(conv.intervention_notes),
            "events": list(conv.events),
            "summary": conv.summary,
            "grade_payload": conv.grade_payload,
        }

    def lab_dashboard(self, lab_id: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate active sessions for professor live view."""
        sessions = []
        for c in self.repo.list_active():
            if lab_id and c.lab_id != lab_id:
                continue
            sessions.append(
                {
                    "conversation_id": c.id,
                    "owner_sub": c.owner_sub,
                    "lab_id": c.lab_id,
                    "lab_score": c.calculate_lab_score(),
                    "goals_done": sum(1 for s in c.goal_progress.values() if s == "done"),
                    "goals_total": len(c.config.learning_context.goals),
                    "hints_revealed": c.hints_revealed,
                    "highest_hint_level": c.highest_hint_level,
                    "frustration_streak": c.frustration_streak,
                    "stuck": c.frustration_streak >= c.config.frustration_threshold,
                    "messages_count": len(c.messages),
                    "in_focus_mode": c.in_focus_mode(),
                    "penalties": sum(
                        1 for m in c.messages if m.role == "assistant" and m.penalty_applied
                    ),
                }
            )
        n = len(sessions)
        avg = round(sum(s["lab_score"] for s in sessions) / n, 2) if n else 0.0
        return {
            "lab_id": lab_id,
            "active_sessions": n,
            "avg_lab_score": avg,
            "total_hints_revealed": sum(s["hints_revealed"] for s in sessions),
            "students_stuck": sum(1 for s in sessions if s["stuck"]),
            "total_penalties": sum(s["penalties"] for s in sessions),
            "sessions": sessions,
        }