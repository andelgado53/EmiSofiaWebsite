"""Unit tests for backend/app/auth.py and backend/app/routers/auth.py."""

from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import patch

import bcrypt
import pytest
from fastapi import HTTPException
from jose import jwt

from app.auth import (
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_HOURS,
    create_access_token,
    get_current_author,
    verify_password,
    verify_token,
)
from app.config import settings


# ---------------------------------------------------------------------------
# create_access_token
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_returns_valid_jwt_string(self):
        with patch.object(settings, "JWT_SECRET", "test-secret"):
            token = create_access_token(sub="author")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_payload_contains_sub_and_exp(self):
        with patch.object(settings, "JWT_SECRET", "test-secret"):
            token = create_access_token(sub="author")
        payload = jwt.decode(token, "test-secret", algorithms=[ALGORITHM])
        assert payload["sub"] == "author"
        assert "exp" in payload

    def test_custom_expires_delta(self):
        with patch.object(settings, "JWT_SECRET", "test-secret"):
            token = create_access_token(sub="author", expires_delta=timedelta(hours=1))
        payload = jwt.decode(token, "test-secret", algorithms=[ALGORITHM])
        assert payload["sub"] == "author"

    def test_default_expiry_is_24_hours(self):
        assert ACCESS_TOKEN_EXPIRE_HOURS == 24

    def test_algorithm_is_hs256(self):
        assert ALGORITHM == "HS256"


# ---------------------------------------------------------------------------
# verify_token
# ---------------------------------------------------------------------------


class TestVerifyToken:
    def test_valid_token_returns_payload(self):
        with patch.object(settings, "JWT_SECRET", "test-secret"):
            token = create_access_token(sub="author")
            payload = verify_token(token)
        assert payload["sub"] == "author"

    def test_invalid_token_raises_401(self):
        with patch.object(settings, "JWT_SECRET", "test-secret"):
            with pytest.raises(HTTPException) as exc_info:
                verify_token("invalid.token.string")
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        with patch.object(settings, "JWT_SECRET", "test-secret"):
            token = create_access_token(
                sub="author", expires_delta=timedelta(seconds=-1)
            )
            with pytest.raises(HTTPException) as exc_info:
                verify_token(token)
        assert exc_info.value.status_code == 401

    def test_token_without_sub_raises_401(self):
        # Manually create a token without 'sub'
        payload = {"exp": 9999999999}
        token = jwt.encode(payload, "test-secret", algorithm=ALGORITHM)
        with patch.object(settings, "JWT_SECRET", "test-secret"):
            with pytest.raises(HTTPException) as exc_info:
                verify_token(token)
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises_401(self):
        token = jwt.encode(
            {"sub": "author", "exp": 9999999999}, "other-secret", algorithm=ALGORITHM
        )
        with patch.object(settings, "JWT_SECRET", "test-secret"):
            with pytest.raises(HTTPException) as exc_info:
                verify_token(token)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# verify_password
# ---------------------------------------------------------------------------


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        password = "my-secret-password"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )
        assert verify_password(password, hashed) is True

    def test_wrong_password_returns_false(self):
        password = "my-secret-password"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )
        assert verify_password("wrong-password", hashed) is False


# ---------------------------------------------------------------------------
# Login endpoint (via TestClient)
# ---------------------------------------------------------------------------


class TestLoginEndpoint:
    @pytest.fixture
    def client(self):
        """Create a test client with mocked settings."""
        from fastapi.testclient import TestClient
        from app.main import app

        return TestClient(app)

    @pytest.fixture
    def password_hash(self):
        """Generate a bcrypt hash for the test password."""
        return bcrypt.hashpw(
            "test-password".encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def test_login_success(self, client, password_hash):
        with patch.object(settings, "CMS_PASSWORD_HASH", password_hash), patch.object(
            settings, "JWT_SECRET", "test-secret"
        ):
            response = client.post(
                "/api/cms/auth/login", json={"password": "test-password"}
            )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, password_hash):
        with patch.object(settings, "CMS_PASSWORD_HASH", password_hash), patch.object(
            settings, "JWT_SECRET", "test-secret"
        ):
            response = client.post(
                "/api/cms/auth/login", json={"password": "wrong-password"}
            )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_no_hash_configured(self, client):
        with patch.object(settings, "CMS_PASSWORD_HASH", ""), patch.object(
            settings, "JWT_SECRET", "test-secret"
        ):
            response = client.post(
                "/api/cms/auth/login", json={"password": "any-password"}
            )
        assert response.status_code == 401

    def test_login_returns_valid_jwt(self, client, password_hash):
        with patch.object(settings, "CMS_PASSWORD_HASH", password_hash), patch.object(
            settings, "JWT_SECRET", "test-secret"
        ):
            response = client.post(
                "/api/cms/auth/login", json={"password": "test-password"}
            )
        token = response.json()["access_token"]
        payload = jwt.decode(token, "test-secret", algorithms=[ALGORITHM])
        assert payload["sub"] == "author"
        assert "exp" in payload
