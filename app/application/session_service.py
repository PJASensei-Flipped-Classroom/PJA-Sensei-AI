import uuid
import time
from typing import Optional, List, Dict, Any, Union

from app.application.dto import GoalProgressEntryDTO, SessionSummaryResponse
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

    def start_conversation(self, config: Union[SenseiConfig, Dict[str, Any]]) -> Conversation:
        if isinstance(config, dict):
            config = SenseiConfig(**config)

        conv_id = str(uuid.uuid4())
        goal_progress: Dict[str, GoalStatus] = {
            goal.id: "not_started" for goal in config.learning_context.goals
        }
        conv = Conversation(
            id=conv_id,
            config=config,
            goal_progress=goal_progress,
            prelab_completed=not config.pre_lab.enabled
        )
        if self.rag is not None and config.reference_materials:
            self.rag.ingest(conv_id, config.reference_materials)

        self.repo.save(conv)
        return conv

    def list_conversations(self) -> List[Dict[str, Any]]:
        all_convs = getattr(self.repo, "_store", {}).values()
        return [
            {
                "conversation_id": c.id,
                "language": c.config.language,
                "lab_score": c.calculate_lab_score(),
                "messages_count": len(c.messages),
                "tokens_used": c.token_usage,
                "prelab_completed": c.prelab_completed,
            }
            for c in all_convs
            if not getattr(c, "is_deleted", False)
        ]

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

        if self.rag is not None:
            self.rag.delete_conversation(conv_id)

        conv.is_deleted = True
        conv.deleted_at = time.time()
        self.repo.save(conv)

        return {
            "status": "deleted",
            "id": conv_id,
            "conversation_id": conv_id,
            "soft_deleted": True,
            "rag_cleaned": True,
            "summary": summary_dict,
        }

    def export(self, conv_id: str) -> dict:
        conv = self.get_or_404(conv_id)
        return conv.model_dump(by_alias=True)

    def record_event(self, conv_id: str, event_type: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        conv = self.get_or_404(conv_id)
        conv.events.append({
            "type": event_type,
            "meta": meta or {},
            "timestamp": time.time(),
        })

        if event_type in ("test_failed", "compile_error", "build_failed", "runtime_error"):
            conv.frustration_streak += 1
        elif event_type in ("test_passed", "goal_completed"):
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

        return {
            "status": "recorded",
            "event_type": event_type,
            "frustration_streak": conv.frustration_streak,
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
            summary_text = (
                f"Podsumowanie sesji laboratoryjnej: wynik {lab_score}% "
                f"(ukończone cele: {len(done_goals)}/{len(goal_entries)}). "
            )
            if done_goals:
                summary_text += f"Zrealizowano: {', '.join(done_goals)}. "
            if pending_goals:
                summary_text += f"Do dopracowania: {', '.join(pending_goals)}."
        else:
            summary_text = (
                f"Lab session summary: score {lab_score}% "
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
        self.repo.save(conv)

        if self.webhooks is not None:
            self.webhooks.send_event(
                "session_summary",
                {"conversation_id": conv.id, "summary": summary_dict},
            )
        return summary_dict

    def generate_summary(self, conv_id: str) -> Dict[str, Any]:
        conv = self.get_or_404(conv_id)
        return self._build_and_store_summary(conv)