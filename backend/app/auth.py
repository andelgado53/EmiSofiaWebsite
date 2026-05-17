"""JWT authentication utilities and FastAPI dependency for CMS routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

# Algorithm used for JWT signing
ALGORITHM = "HS256"

# Default token lifetime
ACCESS_TOKEN_EXPIRE_HOURS = 24

_bearer_scheme = HTTPBearer()


def create_access_token(sub: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        sub: The subject claim (e.g. "author").
        expires_delta: How long until the token expires.
                       Defaults to 24 hours if not provided.

    Returns:
        A signed JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": sub,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The raw JWT string.

    Returns:
        The decoded payload dict.

    Raises:
        HTTPException 401: If the token is invalid, expired, or missing the
                           ``sub`` claim.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception

    sub: str | None = payload.get("sub")
    if sub is None:
        raise credentials_exception

    return payload


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain-text password against a bcrypt hash.

    Args:
        plain: The plain-text password submitted by the user.
        hashed: The bcrypt hash stored in the environment.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def get_current_author(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """FastAPI dependency that validates the ``Authorization: Bearer`` header.

    Attach this to any CMS route that requires authentication::

        @router.get("/api/cms/notes")
        def list_notes(author=Depends(get_current_author)):
            ...

    Returns:
        The decoded JWT payload dict.

    Raises:
        HTTPException 401: If the token is absent, invalid, or expired.
    """
    return verify_token(credentials.credentials)
