"""Conversation ownership and role checks for JWT-backed callers."""
from typing import Any, Dict, Optional

from app.core.config import settings
from app.domain.conversation import Conversation
from app.domain.exceptions import UnknownConversation


def require_professor(claims: Optional[Dict[str, Any]]) -> bool:
    """True when JWT role/roles intersects AI_PROFESSOR_ROLES."""
    if not claims:
        return False
    allowed = {r.lower() for r in (settings.AI_PROFESSOR_ROLES or [])}

    role = claims.get("role")
    if isinstance(role, str) and role.lower() in allowed:
        return True

    roles = claims.get("roles")
    if isinstance(roles, str) and roles.lower() in allowed:
        return True
    if isinstance(roles, list):
        return any(str(r).lower() in allowed for r in roles)
    return False


def ensure_conversation_access(
    conv: Conversation,
    claims: Optional[Dict[str, Any]],
) -> None:
    """
    When AI_AUTH_ENABLED, students may only touch their own sessions.
    Professors bypass. Missing/mismatched owner → UnknownConversation (404).
    """
    if not settings.AI_AUTH_ENABLED:
        return
    if require_professor(claims):
        return
    sub = (claims or {}).get("sub")
    if not conv.owner_sub or not sub or conv.owner_sub != sub:
        raise UnknownConversation(f"Conversation {conv.id} not found")
