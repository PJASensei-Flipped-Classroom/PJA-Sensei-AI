"""JWT verification helpers for optional API authentication."""
from typing import Any, Dict, Optional, Tuple

import jwt

from app.application.access import require_professor  # re-export for API callers
from app.core.config import settings

__all__ = [
    "extract_bearer_token",
    "verify_access_token",
    "require_professor",
    "client_ip_from_request",
]


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    if not authorization_header:
        return None
    parts = authorization_header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def verify_access_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Verify an HS256 JWT with AI_JWT_SECRET.
    Returns (ok, claims, error_detail).
    """
    secret = (settings.AI_JWT_SECRET or "").strip()
    if not secret:
        return False, None, "AI_JWT_SECRET is not configured."

    try:
        # OLD:
        # claims = jwt.decode(
        #     token,
        #     secret,
        #     algorithms=["HS256"],
        #     options={"require": ["exp"]},
        # )
        # Why: bind tokens to this service and require a stable subject for ownership.
        # Wrong: only exp was required — no aud/iss; missing sub broke owner binding.
        # Better: require exp+sub; optionally validate AI_JWT_AUDIENCE / AI_JWT_ISSUER when set.
        decode_kwargs: Dict[str, Any] = {
            "algorithms": ["HS256"],
            "options": {"require": ["exp", "sub"]},
        }
        audience = (settings.AI_JWT_AUDIENCE or "").strip()
        if audience:
            decode_kwargs["audience"] = audience
        issuer = (settings.AI_JWT_ISSUER or "").strip()
        if issuer:
            decode_kwargs["issuer"] = issuer

        claims = jwt.decode(token, secret, **decode_kwargs)
        if not isinstance(claims, dict):
            return False, None, "Invalid token payload."
        return True, claims, None
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired."
    except jwt.InvalidTokenError:
        return False, None, "Invalid or malformed token."


def client_ip_from_request(client_host: Optional[str], x_forwarded_for: Optional[str]) -> str:
    if settings.TRUST_X_FORWARDED_FOR and x_forwarded_for:
        first = x_forwarded_for.split(",")[0].strip()
        if first:
            return first
    return client_host or "unknown"
