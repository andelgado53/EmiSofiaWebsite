"""Unit tests for backend/app/routers/cms_media.py."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_header():
    """Generate a valid Authorization header for CMS requests."""
    with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
        token = create_access_token(sub="author")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_s3():
    """Mock the boto3 S3 client."""
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = (
        "https://s3.amazonaws.com/test-bucket/media/2024/fake-uuid.mp4?presigned=true"
    )
    with patch(
        "app.routers.cms_media.boto3.client", return_value=mock_client
    ):
        yield mock_client


@pytest.fixture
def env_vars():
    """Set required environment variables for tests."""
    return patch.dict(os.environ, {
        "JWT_SECRET": "test-secret",
        "S3_BUCKET": "test-bucket",
        "AWS_REGION": "us-east-1",
        "CLOUDFRONT_DOMAIN": "d1234.cloudfront.net",
    })


class TestMediaPresignEndpoint:
    """Tests for POST /api/cms/media/presign."""

    def test_presign_jpeg_success(self, client, auth_header, mock_s3, env_vars):
        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "photo.jpg", "content_type": "image/jpeg"},
                headers=auth_header,
            )

        assert response.status_code == 200
        data = response.json()
        assert "upload_url" in data
        assert "s3_key" in data
        assert "cdn_url" in data
        assert data["s3_key"].startswith("photos/")
        assert data["s3_key"].endswith(".jpg")
        assert data["cdn_url"].startswith("https://d1234.cloudfront.net/photos/")

    def test_presign_png_success(self, client, auth_header, mock_s3, env_vars):
        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "photo.png", "content_type": "image/png"},
                headers=auth_header,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["s3_key"].startswith("photos/")
        assert data["s3_key"].endswith(".png")
        assert data["cdn_url"].startswith("https://d1234.cloudfront.net/photos/")

    def test_presign_mp4_success(self, client, auth_header, mock_s3, env_vars):
        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "video.mp4", "content_type": "video/mp4"},
                headers=auth_header,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["s3_key"].startswith("videos/")
        assert data["s3_key"].endswith(".mp4")
        assert data["cdn_url"].startswith("https://d1234.cloudfront.net/videos/")

    def test_presign_webm_success(self, client, auth_header, mock_s3, env_vars):
        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "video.webm", "content_type": "video/webm"},
                headers=auth_header,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["s3_key"].startswith("videos/")
        assert data["s3_key"].endswith(".webm")
        assert data["cdn_url"].startswith("https://d1234.cloudfront.net/videos/")

    def test_presign_invalid_content_type_returns_400(self, client, auth_header, env_vars):
        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "doc.pdf", "content_type": "application/pdf"},
                headers=auth_header,
            )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail == "Only image/jpeg, image/png, video/mp4, and video/webm content types are accepted."

    def test_presign_image_gif_returns_400(self, client, auth_header, env_vars):
        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "anim.gif", "content_type": "image/gif"},
                headers=auth_header,
            )

        assert response.status_code == 400

    def test_presign_requires_auth(self, client):
        """Requests without a valid JWT should be rejected."""
        response = client.post(
            "/api/cms/media/presign",
            json={"filename": "video.mp4", "content_type": "video/mp4"},
        )
        assert response.status_code in (401, 403)

    def test_presign_invalid_token_returns_401(self, client):
        """Requests with an invalid JWT should be rejected with 401."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "video.mp4", "content_type": "video/mp4"},
                headers={"Authorization": "Bearer invalid-token"},
            )
        assert response.status_code == 401

    def test_presign_s3_key_format_video(self, client, auth_header, mock_s3, env_vars):
        """S3 key for video should be videos/{year}/{uuid4}.{ext}."""
        current_year = datetime.now(timezone.utc).year

        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "clip.mp4", "content_type": "video/mp4"},
                headers=auth_header,
            )

        data = response.json()
        pattern = rf"^videos/{current_year}/[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}\.mp4$"
        assert re.match(pattern, data["s3_key"]), f"S3 key '{data['s3_key']}' doesn't match expected pattern"

    def test_presign_s3_key_format_photo(self, client, auth_header, mock_s3, env_vars):
        """S3 key for photo should be photos/{year}/{uuid4}.{ext}."""
        current_year = datetime.now(timezone.utc).year

        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "img.jpg", "content_type": "image/jpeg"},
                headers=auth_header,
            )

        data = response.json()
        pattern = rf"^photos/{current_year}/[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}\.jpg$"
        assert re.match(pattern, data["s3_key"]), f"S3 key '{data['s3_key']}' doesn't match expected pattern"

    def test_presign_cdn_url_matches_s3_key(self, client, auth_header, mock_s3, env_vars):
        """CDN URL should be https://{CLOUDFRONT_DOMAIN}/{s3_key}."""
        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "video.webm", "content_type": "video/webm"},
                headers=auth_header,
            )

        data = response.json()
        expected_cdn = f"https://d1234.cloudfront.net/{data['s3_key']}"
        assert data["cdn_url"] == expected_cdn

    def test_presign_calls_boto3_with_correct_params(self, client, auth_header, mock_s3, env_vars):
        """Verify boto3 is called with correct parameters for video."""
        with env_vars:
            response = client.post(
                "/api/cms/media/presign",
                json={"filename": "clip.mp4", "content_type": "video/mp4"},
                headers=auth_header,
            )

        assert response.status_code == 200
        mock_s3.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3.generate_presigned_url.call_args
        assert call_kwargs[1]["ClientMethod"] == "put_object" or call_kwargs[0][0] == "put_object"
        params = call_kwargs[1].get("Params") or call_kwargs[0][1]
        assert params["Bucket"] == "test-bucket"
        assert params["ContentType"] == "video/mp4"
        assert call_kwargs[1].get("ExpiresIn") == 900 or (len(call_kwargs[0]) > 2 and call_kwargs[0][2] == 900)
