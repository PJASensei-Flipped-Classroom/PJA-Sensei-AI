"""Zarządzanie cyklem życia sesji laboratoryjnych: TTL, limity, prelab, idempotencja."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.application.dto import IdeEventRequest
from app.core.config import CONVERSATION_TTL, MAX_CONVERSATIONS, MAX_REVEALS_PER_SESSION
from app.domain.conversation import Conversation, recent_avg_score
from app.domain.exceptions import (
    PrelabRequired,
    TokenBudgetExceeded,
    UnknownConversation,
)
from app.domain.sensei import SenseiConfig
from app.ports import ConversationRepository, RagPort, SummaryPort

logger = logging.getLogger(__name__)


class SessionService:
    """Serwis zarządzający cyklem życia sesji, ograniczeniami i idempotencją."""

    def __init__(
        self,
        conversations: ConversationRepository,
        rag: RagPort,
    ) -> None:
        self._conversations = conversations
        self._rag = rag
        self._summary: SummaryPort | None = None

    def bind_summary(self, summary: SummaryPort) -> None:
        """Późne wiązanie serwisu podsumowań w celu uniknięcia zależności cyklicznej."""
        self._summary = summary

    def conversation_count(self) -> int:
        """Liczba aktywnych sesji w repozytorium (dla /health i metryk)."""
        return len(self._conversations)

    def save_conversation(self, conversation_id: str, conversation: Conversation) -> None:
        """Utrwala bieżący stan agregatu Conversation."""
        self._conversations.save(conversation_id, conversation)

    def purge_stale_conversations(self) -> int:
        """Usuwa wygasłe sesje na podstawie czasu ostatniej aktywności."""
        now = datetime.now(timezone.utc)
        stale_ids = [
            cid
            for cid, conv in self._conversations.items()
            if now - conv.last_active_at > CONVERSATION_TTL
        ]
        for cid in stale_ids:
            self._rag.delete_conversation_data(cid)
            self._conversations.delete(cid)
        return len(stale_ids)

    def _enforce_conversation_cap(self) -> None:
        """Zwalnia najdawniej aktywne sesje (LRU), gdy osiągnięto limit pojemności."""
        if len(self._conversations) < MAX_CONVERSATIONS:
            return

        ordered = sorted(
            self._conversations.items(),
            key=lambda item: item[1].last_active_at,
        )
        overflow_count = len(self._conversations) - MAX_CONVERSATIONS + 1
        for cid, _ in ordered[:overflow_count]:
            self._rag.delete_conversation_data(cid)
            self._conversations.delete(cid)

    def start_conversation(self, problem: str, config: SenseiConfig) -> str:
        """Tworzy i rejestruje nową sesję konwersacyjną."""
        self.purge_stale_conversations()
        self._enforce_conversation_cap()

        conversation_id = str(uuid.uuid4())
        prelab = getattr(config, "pre_lab", None) or getattr(config, "preLab", None)
        prelab_needed = bool(prelab and getattr(prelab, "enabled", False))

        conversation = Conversation(
            problem=problem,
            config=config,
            messages=[],
            prompt_scores=[],
            last_code="",
            prelab_passed=not prelab_needed,
        )
        conversation.ensure_goal_progress_defaults()
        self._conversations.add(conversation_id, conversation)
        return conversation_id

    def get_conversation_or_404(self, conversation_id: str) -> Conversation:
        """Zwraca sesję lub rzuca UnknownConversation (mapowane na HTTP 404)."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            raise UnknownConversation(conversation_id)
        return conversation

    def ensure_prelab_passed(self, conversation: Conversation) -> None:
        """Bramka: czat zablokowany, dopóki prelab niezaliczony (gdy włączony)."""
        prelab = getattr(conversation.config, "pre_lab", None) or getattr(conversation.config, "preLab", None)
        if prelab and getattr(prelab, "enabled", False) and not conversation.prelab_passed:
            raise PrelabRequired()

    def ensure_token_budget(self, conversation: Conversation) -> None:
        """Bramka: wyczerpany max_tokens_per_session → TokenBudgetExceeded."""
        limit = conversation.config.max_tokens_per_session
        if limit is not None and conversation.tokens_used_total >= limit:
            raise TokenBudgetExceeded()

    def get_session_state(self, conversation_id: str) -> dict[str, Any]:
        """Publiczny snapshot stanu sesji dla GET /conversations/{id}."""
        conv = self.get_conversation_or_404(conversation_id)
        conv.touch()
        avg = recent_avg_score(conv.prompt_scores)
        prelab = getattr(conv.config, "pre_lab", None) or getattr(conv.config, "preLab", None)
        ide_restrictions = getattr(conv.config, "ide_restrictions", None) or getattr(conv.config, "ideRestrictions", None)

        return {
            "conversation_id": conversation_id,
            "problem": conv.problem,
            "language": conv.config.language,
            "goals": conv.config.learning_context.goals,
            "ideRestrictions": ide_restrictions.model_dump() if ide_restrictions else None,
            "prelab_passed": conv.prelab_passed,
            "prelab_required": bool(prelab and getattr(prelab, "enabled", False)),
            "message_count": len(conv.messages),
            "avg_score": round(avg, 2),
            "tokens_used_total": conv.tokens_used_total,
            "max_tokens_per_session": conv.config.max_tokens_per_session,
            "is_frustrated": conv.is_frustrated,
            "reveal_count": conv.reveal_count,
            "max_reveals_per_session": MAX_REVEALS_PER_SESSION,
            "ide_event_count": len(conv.ide_events),
            "mode": getattr(conv.config.agent_behavior, "mode", "debug"),
            "unlocked_checkpoints": list(conv.unlocked_checkpoints),
            "prelab_attempts": conv.prelab_attempts,
            "last_prelab_score": conv.last_prelab_score,
        }

    def get_message_history(self, conversation_id: str) -> dict[str, Any]:
        """Zwraca sformatowaną historię wiadomości."""
        conv = self.get_conversation_or_404(conversation_id)
        conv.touch()
        items = []

        for m in conv.messages:
            role = m.get("role")
            if role not in ("user", "assistant"):
                continue

            content = m.get("content", "")
            # Preferuj zapisaną czystą treść pytania, jeśli istnieje
            display_content = m.get("raw_question") or content

            items.append({
                "role": role,
                "content": display_content,
                "message_id": m.get("message_id"),
                "prompt_score": m.get("prompt_score"),
                "penalty_applied": m.get("penalty_applied", False),
                "sources": m.get("sources") or [],
                "suggested_next_step": m.get("suggested_next_step"),
                "goal_progress": m.get("goal_progress") or [],
                "next_checkpoint": m.get("next_checkpoint"),
            })

        return {"conversation_id": conversation_id, "messages": items}

    def get_restrictions(self, conversation_id: str) -> dict[str, Any]:
        conv = self.get_conversation_or_404(conversation_id)
        restr = getattr(conv.config, "ide_restrictions", None) or getattr(conv.config, "ideRestrictions", None)
        prelab = getattr(conv.config, "pre_lab", None) or getattr(conv.config, "preLab", None)

        return {
            "conversation_id": conversation_id,
            "requireFileContextForChat": bool(restr and getattr(restr, "require_file_context_for_chat", False)),
            "disableCopyFromChat": bool(restr and getattr(restr, "disable_copy_from_chat", False)),
            "maxTokensPerSession": conv.config.max_tokens_per_session,
            "prelab_required": bool(prelab and getattr(prelab, "enabled", False)),
            "prelab_passed": conv.prelab_passed,
        }

    def record_ide_event(self, conversation_id: str, payload: IdeEventRequest) -> dict[str, Any]:
        conv = self.get_conversation_or_404(conversation_id)
        event = {
            "type": payload.type,
            "meta": payload.meta,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        conv.ide_events.append(event)
        conv.touch()
        self.save_conversation(conversation_id, conv)
        return {"status": "ok", "event": event, "total_events": len(conv.ide_events)}

    def record_message_feedback(
        self,
        conversation_id: str,
        message_id: str,
        *,
        rating: int,
        comment: str | None,
    ) -> dict[str, Any]:
        conv = self.get_conversation_or_404(conversation_id)
        target = next((m for m in conv.messages if m.get("message_id") == message_id), None)
        if target is None:
            raise KeyError("message_not_found")

        target["student_feedback"] = {"rating": rating, "comment": comment}
        conv.touch()
        self.save_conversation(conversation_id, conv)
        return {"status": "success", "message_id": message_id}

    def export_conversation(self, conversation_id: str) -> dict[str, Any]:
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

    def get_checkpoints(self, conversation_id: str) -> dict[str, Any]:
        conv = self.get_conversation_or_404(conversation_id)
        conv.ensure_goal_progress_defaults()
        done_goals = {g["goal"] for g in conv.goal_progress if g.get("status") == "done"}

        items = []
        for cp in conv.config.checkpoints:
            is_unlocked = cp.id in conv.unlocked_checkpoints or cp.after_goal is None or cp.after_goal in done_goals
            if is_unlocked and cp.id not in conv.unlocked_checkpoints:
                conv.unlocked_checkpoints.append(cp.id)

            items.append({
                "id": cp.id,
                "after_goal": cp.after_goal,
                "hint": cp.hint,
                "unlocked": is_unlocked,
            })

        conv.touch()
        self.save_conversation(conversation_id, conv)
        return {"conversation_id": conversation_id, "checkpoints": items}

    def lookup_idempotent(self, conversation_id: str, client_message_id: str | None) -> dict[str, Any] | None:
        if not client_message_id:
            return None
        conv = self.get_conversation_or_404(conversation_id)
        if cached := conv.idempotency.get(client_message_id):
            result = dict(cached)
            result["is_cached"] = True
            result["client_message_id"] = client_message_id
            return result
        return None

    def store_idempotent(
        self, conversation_id: str, client_message_id: str | None, result: dict[str, Any]
    ) -> dict[str, Any]:
        if not client_message_id:
            return result

        conv = self.get_conversation_or_404(conversation_id)
        payload = dict(result)
        payload["client_message_id"] = client_message_id
        conv.idempotency[client_message_id] = payload
        self.save_conversation(conversation_id, conv)
        return payload

    async def delete_conversation(
        self, conversation_id: str, *, generate_summary_on_delete: bool = True
    ) -> dict[str, Any]:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise UnknownConversation(conversation_id)

        summary = None
        if generate_summary_on_delete and not conv.summary_generated and conv.messages and self._summary:
            try:
                summary = await self._summary.generate_summary(conversation_id)
            except Exception as exc:
                logger.warning("Generowanie podsumowania podczas usuwania nie powiodło się: %s", exc)

        self._conversations.delete(conversation_id)
        self._rag.delete_conversation_data(conversation_id)
        return {
            "status": "deleted",
            "conversation_id": conversation_id,
            "summary": summary,
        }