"""CMS authentication router — login endpoint."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from app.auth import ACCESS_TOKEN_EXPIRE_HOURS, create_access_token, verify_password
from app.config import settings
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/cms/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange CMS password for a JWT access token",
)
def login(body: LoginRequest) -> TokenResponse:
    """Authenticate the author and return a JWT.

    The submitted password is verified against the bcrypt hash stored in the
    ``CMS_PASSWORD_HASH`` environment variable.  On success a 24-hour JWT is
    returned.  On failure a ``401 Unauthorized`` response is returned — the
    same response is used whether the hash is missing or the password is wrong,
    to avoid leaking configuration state.
    """
    password_hash = settings.CMS_PASSWORD_HASH

    # Reject immediately if no hash is configured (misconfigured deployment)
    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(body.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        sub="author",
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    )
    return TokenResponse(access_token=access_token)
