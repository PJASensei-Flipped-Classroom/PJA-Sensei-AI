import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import AI_AUTH_ENABLED, AI_JWT_ALGORITHM, AI_JWT_SECRET

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """Validate Bearer JWT when AI_AUTH_ENABLED. Returns subject or None if auth off."""
    if not AI_AUTH_ENABLED:
        return None

    if not AI_JWT_SECRET:
        logger.error("AI_AUTH_ENABLED but AI_JWT_SECRET is empty")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth misconfigured",
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        import jwt

        payload = jwt.decode(
            credentials.credentials,
            AI_JWT_SECRET,
            algorithms=[AI_JWT_ALGORITHM],
        )
    except Exception as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )
    return str(sub)
