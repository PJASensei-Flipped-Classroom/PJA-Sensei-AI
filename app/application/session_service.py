import uuid
from app.domain.conversation import Conversation
from app.domain.ports import ConversationRepository
from app.domain.sensei import SenseiConfig
from app.domain.exceptions import UnknownConversation, PrelabRequired
from app.core.config import settings

class SessionService:
    def __init__(self, repo: ConversationRepository):
        self.repo = repo

    def start_conversation(self, config: SenseiConfig) -> Conversation:
        conv_id = str(uuid.uuid4())
        goal_progress = {goal.id: "not_started" for goal in config.learning_context.goals}
        conv = Conversation(
            id=conv_id,
            config=config,
            goal_progress=goal_progress,
            prelab_completed=not config.pre_lab.enabled
        )
        self.repo.save(conv)
        return conv
    def get_or_404(self, conv_id: str) -> Conversation:
        conv = self.repo.get(conv_id)
        if not conv:
            raise UnknownConversation(f"Conversation {conv_id} not found")
        return conv

    def delete(self, conv_id: str) -> bool:
        if not self.repo.delete(conv_id):
            raise UnknownConversation(f"Conversation {conv_id} not found")
        return True

    def export(self, conv_id: str) -> dict:
        conv = self.get_or_404(conv_id)
        return conv.model_dump(by_alias=True)

    def record_event(self, conv_id: str, event_type: dict, meta: dict):
        conv = self.get_or_404(conv_id)
        pass

    def purge_old_sessions(self) -> int:
        return self.repo.purge_expired(settings.CONVERSATION_TTL_SECONDS)

    def ensure_prelab_passed(self, conv_id: str) -> Conversation:
        conv = self.get_or_404(conv_id)
        if conv.config.pre_lab.enabled and not conv.prelab_completed:
            raise PrelabRequired(conv.config.language)
        return conv