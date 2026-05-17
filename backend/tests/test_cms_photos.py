"""Unit tests for backend/app/routers/cms_photos.py."""

from __future__ import annotations

import os

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.config import settings
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
        "https://s3.amazonaws.com/test-bucket/photos/2024/fake-uuid.jpg?presigned=true"
    )
    with patch(
        "app.routers.cms_photos.boto3.client", return_value=mock_client
    ) as mock_boto:
        yield mock_client


class TestPresignEndpoint:
    """Tests for POST /api/cms/photos/presign."""

    def test_presign_jpeg_success(self, client, auth_header, mock_s3):
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}), \
             patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}), \
             patch.dict(os.environ, {"AWS_REGION": "us-east-1"}), \
             patch.dict(os.environ, {"CLOUDFRONT_DOMAIN": "d1234.cloudfront.net"}):
            response = client.post(
                "/api/cms/photos/presign",
                json={"filename": "photo.jpg", "content_type": "image/jpeg"},
                headers=auth_header,
            )

        assert response.status_code == 200
        data = response.json()
        assert "upload_url" in data
        assert "s3_key" in data
        assert "cdn_url" in data
        # S3 key should follow photos/{year}/{uuid}.jpg pattern
        assert data["s3_key"].startswith("photos/")
        assert data["s3_key"].endswith(".jpg")
        # CDN URL should use the CloudFront domain
        assert data["cdn_url"].startswith("https://d1234.cloudfront.net/photos/")

    def test_presign_png_success(self, client, auth_header, mock_s3):
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}), \
             patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}), \
             patch.dict(os.environ, {"AWS_REGION": "us-east-1"}), \
             patch.dict(os.environ, {"CLOUDFRONT_DOMAIN": "d1234.cloudfront.net"}):
            response = client.post(
                "/api/cms/photos/presign",
                json={"filename": "photo.png", "content_type": "image/png"},
                headers=auth_header,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["s3_key"].endswith(".png")
        assert data["cdn_url"].startswith("https://d1234.cloudfront.net/photos/")

    def test_presign_invalid_content_type_returns_400(self, client, auth_header):
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/photos/presign",
                json={"filename": "doc.pdf", "content_type": "application/pdf"},
                headers=auth_header,
            )

        assert response.status_code == 400
        assert "jpeg" in response.json()["detail"].lower() or "png" in response.json()["detail"].lower()

    def test_presign_image_gif_returns_400(self, client, auth_header):
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/photos/presign",
                json={"filename": "anim.gif", "content_type": "image/gif"},
                headers=auth_header,
            )

        assert response.status_code == 400

    def test_presign_requires_auth(self, client):
        """Requests without a valid JWT should be rejected."""
        response = client.post(
            "/api/cms/photos/presign",
            json={"filename": "photo.jpg", "content_type": "image/jpeg"},
        )
        # HTTPBearer returns 403 when header is missing, or 401 depending on config
        assert response.status_code in (401, 403)

    def test_presign_invalid_token_returns_401(self, client):
        """Requests with an invalid JWT should be rejected with 401."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/photos/presign",
                json={"filename": "photo.jpg", "content_type": "image/jpeg"},
                headers={"Authorization": "Bearer invalid-token"},
            )
        assert response.status_code == 401

    def test_presign_s3_key_format(self, client, auth_header, mock_s3):
        """S3 key should be photos/{year}/{uuid4}.{ext}."""
        import re
        from datetime import datetime, timezone

        current_year = datetime.now(timezone.utc).year

        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}), \
             patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}), \
             patch.dict(os.environ, {"AWS_REGION": "us-east-1"}), \
             patch.dict(os.environ, {"CLOUDFRONT_DOMAIN": "d1234.cloudfront.net"}):
            response = client.post(
                "/api/cms/photos/presign",
                json={"filename": "photo.jpg", "content_type": "image/jpeg"},
                headers=auth_header,
            )

        data = response.json()
        # Should match photos/{year}/{uuid4}.jpg
        pattern = rf"^photos/{current_year}/[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}\.jpg$"
        assert re.match(pattern, data["s3_key"]), f"S3 key '{data['s3_key']}' doesn't match expected pattern"

    def test_presign_calls_boto3_with_correct_params(self, client, auth_header, mock_s3):
        """Verify boto3 is called with correct parameters."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}), \
             patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}), \
             patch.dict(os.environ, {"AWS_REGION": "us-east-1"}), \
             patch.dict(os.environ, {"CLOUDFRONT_DOMAIN": "d1234.cloudfront.net"}):
            response = client.post(
                "/api/cms/photos/presign",
                json={"filename": "photo.jpg", "content_type": "image/jpeg"},
                headers=auth_header,
            )

        assert response.status_code == 200
        # Verify generate_presigned_url was called
        mock_s3.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3.generate_presigned_url.call_args
        assert call_kwargs[1]["ClientMethod"] == "put_object" or call_kwargs[0][0] == "put_object"
        params = call_kwargs[1].get("Params") or call_kwargs[0][1]
        assert params["Bucket"] == "test-bucket"
        assert params["ContentType"] == "image/jpeg"
        assert call_kwargs[1].get("ExpiresIn") == 900 or (len(call_kwargs[0]) > 2 and call_kwargs[0][2] == 900)


class TestDeletePhotoEndpoint:
    """Tests for DELETE /api/cms/photos/{key}."""

    def test_delete_photo_success(self, client, auth_header, mock_s3):
        """Deleting a photo returns 204 and calls S3 delete_object."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}), \
             patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}), \
             patch.dict(os.environ, {"AWS_REGION": "us-east-1"}):
            response = client.delete(
                "/api/cms/photos/photos/2024/abc123.jpg",
                headers=auth_header,
            )

        assert response.status_code == 204
        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="photos/2024/abc123.jpg"
        )

    def test_delete_photo_url_decodes_key(self, client, auth_header, mock_s3):
        """URL-encoded characters in the key are decoded before calling S3."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}), \
             patch.dict(os.environ, {"S3_BUCKET": "test-bucket"}), \
             patch.dict(os.environ, {"AWS_REGION": "us-east-1"}):
            response = client.delete(
                "/api/cms/photos/photos/2024/my%20photo%20file.jpg",
                headers=auth_header,
            )

        assert response.status_code == 204
        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="photos/2024/my photo file.jpg"
        )

    def test_delete_photo_requires_auth(self, client):
        """Requests without a valid JWT should be rejected."""
        response = client.delete("/api/cms/photos/photos/2024/abc123.jpg")
        assert response.status_code in (401, 403)

    def test_delete_photo_invalid_token_returns_401(self, client):
        """Requests with an invalid JWT should be rejected with 401."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.delete(
                "/api/cms/photos/photos/2024/abc123.jpg",
                headers={"Authorization": "Bearer invalid-token"},
            )
        assert response.status_code == 401
