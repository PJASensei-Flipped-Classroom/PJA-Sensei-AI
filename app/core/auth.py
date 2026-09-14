"""JWT Bearer authentication dependency."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import AI_AUTH_ENABLED, AI_JWT_ALGORITHM, AI_JWT_SECRET

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    """Kontekst uwierzytelnionego użytkownika."""
    subject: str
    is_authenticated: bool = True


async def require_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> AuthUser | None:
    """Weryfikuje token Bearer JWT. Zwraca obiekt użytkownika lub None przy wyłączonym auth."""
    if not AI_AUTH_ENABLED:
        return None

    if not AI_JWT_SECRET:
        logger.critical("AI_AUTH_ENABLED jest aktywne, lecz AI_JWT_SECRET nie zostało skonfigurowane.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Błąd konfiguracji serwera uwierzytelniania.",
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wymagany nagłówek Authorization: Bearer ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            AI_JWT_SECRET,
            algorithms=[AI_JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        logger.info("Próba użycia wygasłego tokenu JWT: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token dostępowy wygasł.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"token expired\""},
        ) from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("Niepoprawny token JWT: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token uwierzytelniający.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nie zawiera wymaganego identyfikatora podmiotu (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(subject=str(subject))