from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.api.schemas.requests import IdeEventRequest
from app.core.config import CONVERSATION_TTL, MAX_CONVERSATIONS
from app.domain.conversation import Conversation, recent_avg_score
from app.domain.exceptions import (
    PrelabRequired,
    TokenBudgetExceeded,
    UnknownConversation,
)
from app.domain.sensei import SenseiConfig

if TYPE_CHECKING:
    from app.application.container import AppContainer

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, app: AppContainer) -> None:
        self._app = app

    def purge_stale_conversations(self) -> int:
        now = datetime.now(timezone.utc)
        stale = [
            cid
            for cid, conv in self._app.conversations.items()
            if now - conv.last_active_at > CONVERSATION_TTL
        ]
        for cid in stale:
            self._app.rag.delete_conversation_data(cid)
            del self._app.conversations[cid]
        return len(stale)

    def _enforce_conversation_cap(self) -> None:
        if len(self._app.conversations) < MAX_CONVERSATIONS:
            return
        ordered = sorted(
            self._app.conversations.items(), key=lambda item: item[1].last_active_at
        )
        overflow = len(self._app.conversations) - MAX_CONVERSATIONS + 1
        for cid, _ in ordered[:overflow]:
            self._app.rag.delete_conversation_data(cid)
            del self._app.conversations[cid]

    def start_conversation(self, problem: str, config: SenseiConfig) -> str:
        self.purge_stale_conversations()
        self._enforce_conversation_cap()
        conversation_id = str(uuid.uuid4())
        prelab_needed = bool(config.preLab and config.preLab.enabled)
        self._app.conversations[conversation_id] = Conversation(
            problem=problem,
            config=config,
            messages=[],
            prompt_scores=[],
            last_code="",
            prelab_passed=not prelab_needed,
        )
        self._app.conversations[conversation_id].ensure_goal_progress_defaults()
        return conversation_id

    def get_conversation_or_404(self, conversation_id: str) -> Conversation:
        conversation = self._app.conversations.get(conversation_id)
        if not conversation:
            raise UnknownConversation(conversation_id)
        return conversation

    def ensure_prelab_passed(self, conversation: Conversation) -> None:
        prelab = conversation.config.preLab
        if prelab and prelab.enabled and not conversation.prelab_passed:
            raise PrelabRequired()

    def ensure_token_budget(self, conversation: Conversation) -> None:
        limit = conversation.config.maxTokensPerSession
        if limit is not None and conversation.tokens_used_total >= limit:
            raise TokenBudgetExceeded()

    def get_session_state(self, conversation_id: str) -> dict:
        conv = self.get_conversation_or_404(conversation_id)
        conv.touch()
        avg = recent_avg_score(conv.prompt_scores)
        return {
            "conversation_id": conversation_id,
            "problem": conv.problem,
            "language": conv.config.language,
            "goals": conv.config.learningContext.goals,
            "ideRestrictions": (
                conv.config.ideRestrictions.model_dump()
                if conv.config.ideRestrictions
                else None
            ),
            "prelab_passed": conv.prelab_passed,
            "prelab_required": bool(conv.config.preLab and conv.config.preLab.enabled),
            "message_count": len(conv.messages),
            "avg_score": round(avg, 2),
            "tokens_used_total": conv.tokens_used_total,
            "max_tokens_per_session": conv.config.maxTokensPerSession,
            "is_frustrated": conv.is_frustrated,
            "reveal_count": conv.reveal_count,
            "ide_event_count": len(conv.ide_events),
            "mode": conv.config.agentBehavior.mode,
            "unlocked_checkpoints": list(conv.unlocked_checkpoints),
            "prelab_attempts": conv.prelab_attempts,
            "last_prelab_score": conv.last_prelab_score,
        }

    def get_message_history(self, conversation_id: str) -> dict:
        conv = self.get_conversation_or_404(conversation_id)
        conv.touch()
        items = []
        for m in conv.messages:
            role = m.get("role")
            if role not in ("user", "assistant"):
                continue
            content = m.get("content", "")
            if role == "user":
                # Prefer the student question line if present
                match = re.search(
                    r"(?:Student question|Pytanie studenta):\s*(.*)$",
                    content,
                    re.MULTILINE,
                )
                content = match.group(1).strip() if match else content[:500]
            items.append(
                {
                    "role": role,
                    "content": content,
                    "message_id": m.get("message_id"),
                    "prompt_score": m.get("prompt_score"),
                    "penalty_applied": m.get("penalty_applied", False),
                    "sources": m.get("sources") or [],
                    "suggested_next_step": m.get("suggested_next_step"),
                    "goal_progress": m.get("goal_progress") or [],
                }
            )
        return {"conversation_id": conversation_id, "messages": items}

    def get_restrictions(self, conversation_id: str) -> dict:
        conv = self.get_conversation_or_404(conversation_id)
        restrictions = conv.config.ideRestrictions
        return {
            "conversation_id": conversation_id,
            "requireFileContextForChat": bool(
                restrictions and restrictions.requireFileContextForChat
            ),
            "disableCopyFromChat": bool(
                restrictions and restrictions.disableCopyFromChat
            ),
            "maxTokensPerSession": conv.config.maxTokensPerSession,
            "prelab_required": bool(conv.config.preLab and conv.config.preLab.enabled),
            "prelab_passed": conv.prelab_passed,
        }

    def record_ide_event(self, conversation_id: str, payload: IdeEventRequest) -> dict:
        conv = self.get_conversation_or_404(conversation_id)
        event = {
            "type": payload.type,
            "meta": payload.meta,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        conv.ide_events.append(event)
        conv.touch()
        return {"status": "ok", "event": event, "total_events": len(conv.ide_events)}

    def export_conversation(self, conversation_id: str) -> dict:
        conv = self.get_conversation_or_404(conversation_id)
        conv.touch()
        history = self.get_message_history(conversation_id)
        return {
            "conversation_id": conversation_id,
            "problem": conv.problem,
            "config": conv.config.model_dump(),
            "messages": history["messages"],
            "prompt_scores": list(conv.prompt_scores),
            "ide_events": list(conv.ide_events),
            "goal_progress": list(conv.goal_progress),
            "unlocked_checkpoints": list(conv.unlocked_checkpoints),
            "tokens_used_total": conv.tokens_used_total,
            "prelab_passed": conv.prelab_passed,
            "prelab_attempts": conv.prelab_attempts,
            "last_prelab_score": conv.last_prelab_score,
            "summary": conv.last_summary,
            "summary_generated": conv.summary_generated,
            "created_at": conv.created_at.isoformat(),
            "last_active_at": conv.last_active_at.isoformat(),
        }

    def get_checkpoints(self, conversation_id: str) -> dict:
        conv = self.get_conversation_or_404(conversation_id)
        conv.ensure_goal_progress_defaults()
        done_goals = {
            g["goal"] for g in conv.goal_progress if g.get("status") == "done"
        }
        items = []
        for cp in conv.config.checkpoints:
            unlocked = cp.id in conv.unlocked_checkpoints or (
                cp.after_goal is None or cp.after_goal in done_goals
            )
            if unlocked and cp.id not in conv.unlocked_checkpoints:
                conv.unlocked_checkpoints.append(cp.id)
            items.append(
                {
                    "id": cp.id,
                    "after_goal": cp.after_goal,
                    "hint": cp.hint,
                    "unlocked": cp.id in conv.unlocked_checkpoints
                    or (cp.after_goal is None or cp.after_goal in done_goals),
                }
            )
        conv.touch()
        return {"conversation_id": conversation_id, "checkpoints": items}

    def lookup_idempotent(
        self, conversation_id: str, client_message_id: str | None
    ) -> dict | None:
        if not client_message_id:
            return None
        conv = self.get_conversation_or_404(conversation_id)
        cached = conv.idempotency.get(client_message_id)
        if cached:
            result = dict(cached)
            result["is_cached"] = True
            result["client_message_id"] = client_message_id
            return result
        return None

    def store_idempotent(
        self, conversation_id: str, client_message_id: str | None, result: dict
    ) -> dict:
        if client_message_id:
            conv = self.get_conversation_or_404(conversation_id)
            payload = dict(result)
            payload["client_message_id"] = client_message_id
            conv.idempotency[client_message_id] = payload
            result = payload
        return result

    async def delete_conversation(
        self, conversation_id: str, *, soft_summary: bool = True
    ) -> dict:
        conv = self._app.conversations.get(conversation_id)
        if conv is None:
            raise UnknownConversation(conversation_id)
        summary = None
        if soft_summary and not conv.summary_generated and conv.messages:
            try:
                summary = await self._app.summary.generate_summary(conversation_id)
            except Exception as exc:
                logger.warning("Soft summary on delete failed: %s", exc)
        self._app.conversations.pop(conversation_id, None)
        self._app.rag.delete_conversation_data(conversation_id)
        return {
            "status": "deleted",
            "conversation_id": conversation_id,
            "summary": summary,
        }
