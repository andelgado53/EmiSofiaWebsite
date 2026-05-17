"""Backend integration tests — full API flow with in-memory SQLite.

Covers:
- Full CRUD lifecycle (create draft → publish → edit → delete)
- Auth (valid login, wrong password, missing token, expired token)
- Photo presign (valid types, invalid type, note with 2 photos then attempt a third)
- Public API (published notes appear, drafts do not; ordering by published_at DESC)
- ISR revalidation flow (CMS publish triggers revalidation)

Requirements: 5.1–5.8, 6.8, 3.1–3.2
"""

from __future__ import annotations

import os

from datetime import timedelta
from unittest.mock import patch, MagicMock

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token, ALGORITHM
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import Note


# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Module-level test password and hash
TEST_PASSWORD = "integration-test-password"
TEST_PASSWORD_HASH = bcrypt.hashpw(
    TEST_PASSWORD.encode("utf-8"), bcrypt.gensalt()
).decode("utf-8")
TEST_JWT_SECRET = "integration-test-jwt-secret"


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test and drop them after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_header():
    """Return a valid Authorization header."""
    with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
        token = create_access_token(sub="author")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def settings_patch():
    """Context manager that patches all settings needed for integration tests."""
    with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}), \
         patch.dict(os.environ, {"CMS_PASSWORD_HASH": TEST_PASSWORD_HASH}):
        yield


# ===========================================================================
# AUTH INTEGRATION TESTS
# ===========================================================================


class TestAuthIntegration:
    """Auth flow: valid login, wrong password, missing token, expired token."""

    def test_login_success_returns_jwt(self, client):
        """Valid password returns a JWT that can be used on CMS endpoints."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}), \
             patch.dict(os.environ, {"CMS_PASSWORD_HASH": TEST_PASSWORD_HASH}):
            # Login
            resp = client.post(
                "/api/cms/auth/login",
                json={"password": TEST_PASSWORD},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Use the token to access a CMS endpoint
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            cms_resp = client.get(
                "/api/cms/notes",
                headers={"Authorization": f"Bearer {data['access_token']}"},
            )
        assert cms_resp.status_code == 200

    def test_login_wrong_password(self, client):
        """Wrong password returns 401."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}), \
             patch.dict(os.environ, {"CMS_PASSWORD_HASH": TEST_PASSWORD_HASH}):
            resp = client.post(
                "/api/cms/auth/login",
                json={"password": "wrong-password"},
            )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    def test_missing_token_rejected(self, client):
        """CMS endpoints reject requests without Authorization header."""
        resp = client.get("/api/cms/notes")
        assert resp.status_code in (401, 403)

        resp = client.post("/api/cms/notes", json={"title": "X", "body_html": "<p>Y</p>"})
        assert resp.status_code in (401, 403)

    def test_expired_token_rejected(self, client):
        """An expired JWT is rejected with 401."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            expired_token = create_access_token(
                sub="author", expires_delta=timedelta(seconds=-10)
            )
            resp = client.get(
                "/api/cms/notes",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
        assert resp.status_code == 401

    def test_invalid_token_string_rejected(self, client):
        """A garbage token string is rejected."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            resp = client.get(
                "/api/cms/notes",
                headers={"Authorization": "Bearer not.a.valid.jwt.token"},
            )
        assert resp.status_code == 401

    def test_token_signed_with_wrong_secret_rejected(self, client):
        """A JWT signed with a different secret is rejected."""
        from jose import jwt as jose_jwt

        wrong_token = jose_jwt.encode(
            {"sub": "author", "exp": 9999999999},
            "wrong-secret",
            algorithm=ALGORITHM,
        )
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            resp = client.get(
                "/api/cms/notes",
                headers={"Authorization": f"Bearer {wrong_token}"},
            )
        assert resp.status_code == 401


# ===========================================================================
# FULL CRUD LIFECYCLE INTEGRATION TESTS
# ===========================================================================


class TestCrudLifecycle:
    """Full lifecycle: create draft → publish → edit → delete."""

    def test_full_note_lifecycle(self, client, auth_header):
        """End-to-end: create draft, publish, edit, verify public, delete."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            # Step 1: Create a draft note
            create_resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "My First Note",
                    "body_html": "<p>Hello Emi, this is a draft.</p>",
                    "labels": ["life", "lessons"],
                },
                headers=auth_header,
            )
            assert create_resp.status_code == 201
            note = create_resp.json()
            note_id = note["id"]
            assert note["status"] == "draft"
            assert note["published_at"] is None
            assert len(note["labels"]) == 2

            # Step 2: Draft should NOT appear in public API
            public_resp = client.get("/api/notes")
            assert public_resp.status_code == 200
            assert public_resp.json()["total"] == 0

            public_detail = client.get(f"/api/notes/{note_id}")
            assert public_detail.status_code == 404

            # Step 3: Publish the note
            publish_resp = client.put(
                f"/api/cms/notes/{note_id}",
                json={"status": "published"},
                headers=auth_header,
            )
            assert publish_resp.status_code == 200
            published = publish_resp.json()
            assert published["status"] == "published"
            assert published["published_at"] is not None

            # Step 4: Published note appears in public API
            public_resp = client.get("/api/notes")
            assert public_resp.status_code == 200
            items = public_resp.json()["items"]
            assert len(items) == 1
            assert items[0]["title"] == "My First Note"

            public_detail = client.get(f"/api/notes/{note_id}")
            assert public_detail.status_code == 200
            detail = public_detail.json()
            assert detail["title"] == "My First Note"
            assert detail["body_html"] == "<p>Hello Emi, this is a draft.</p>"

            # Step 5: Edit the published note
            edit_resp = client.put(
                f"/api/cms/notes/{note_id}",
                json={
                    "title": "My Updated Note",
                    "body_html": "<p>Updated content for Emi.</p>",
                    "labels": ["updated"],
                },
                headers=auth_header,
            )
            assert edit_resp.status_code == 200
            updated = edit_resp.json()
            assert updated["title"] == "My Updated Note"
            assert updated["body_html"] == "<p>Updated content for Emi.</p>"

            # Step 6: Verify edit is reflected in public API
            public_detail = client.get(f"/api/notes/{note_id}")
            assert public_detail.status_code == 200
            assert public_detail.json()["title"] == "My Updated Note"
            label_names = [l["name"] for l in public_detail.json()["labels"]]
            assert label_names == ["updated"]

            # Step 7: Delete the note
            delete_resp = client.delete(
                f"/api/cms/notes/{note_id}", headers=auth_header
            )
            assert delete_resp.status_code == 204

            # Step 8: Deleted note no longer in public API
            public_resp = client.get("/api/notes")
            assert public_resp.json()["total"] == 0

            public_detail = client.get(f"/api/notes/{note_id}")
            assert public_detail.status_code == 404

            # Step 9: Deleted note no longer in CMS API
            cms_detail = client.get(
                f"/api/cms/notes/{note_id}", headers=auth_header
            )
            assert cms_detail.status_code == 404

    def test_create_note_with_photos_and_labels(self, client, auth_header):
        """Create a note with photos and labels, verify all data persists."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "Photo Note",
                    "body_html": "<p>A note with photos.</p>",
                    "status": "published",
                    "labels": ["family", "photos"],
                    "photos": [
                        {
                            "s3_key": "photos/2024/img1.jpg",
                            "cdn_url": "https://cdn.example.com/photos/2024/img1.jpg",
                            "position": 1,
                        },
                        {
                            "s3_key": "photos/2024/img2.png",
                            "cdn_url": "https://cdn.example.com/photos/2024/img2.png",
                            "position": 2,
                        },
                    ],
                },
                headers=auth_header,
            )
            assert resp.status_code == 201
            note = resp.json()
            note_id = note["id"]
            assert len(note["photos"]) == 2
            assert len(note["labels"]) == 2

            # Verify via public detail endpoint
            detail = client.get(f"/api/notes/{note_id}")
            assert detail.status_code == 200
            data = detail.json()
            assert data["photos"][0]["position"] == 1
            assert data["photos"][1]["position"] == 2
            assert "cdn.example.com" in data["photos"][0]["cdn_url"]
            label_names = sorted([l["name"] for l in data["labels"]])
            assert label_names == ["family", "photos"]

    def test_multiple_notes_crud(self, client, auth_header):
        """Create multiple notes, verify list, delete one, verify list again."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            # Create 3 published notes
            ids = []
            for i in range(3):
                resp = client.post(
                    "/api/cms/notes",
                    json={
                        "title": f"Note {i}",
                        "body_html": f"<p>Body {i}</p>",
                        "status": "published",
                    },
                    headers=auth_header,
                )
                assert resp.status_code == 201
                ids.append(resp.json()["id"])

            # All 3 appear in public list
            public_resp = client.get("/api/notes")
            assert public_resp.json()["total"] == 3

            # Delete the middle one
            del_resp = client.delete(
                f"/api/cms/notes/{ids[1]}", headers=auth_header
            )
            assert del_resp.status_code == 204

            # Now only 2 remain
            public_resp = client.get("/api/notes")
            assert public_resp.json()["total"] == 2

            # The deleted one returns 404
            assert client.get(f"/api/notes/{ids[1]}").status_code == 404

            # The others still exist
            assert client.get(f"/api/notes/{ids[0]}").status_code == 200
            assert client.get(f"/api/notes/{ids[2]}").status_code == 200


# ===========================================================================
# PHOTO PRESIGN INTEGRATION TESTS
# ===========================================================================


class TestPhotoPresignIntegration:
    """Photo presign: valid types, invalid type, max 2 photos per note."""

    def test_presign_jpeg_accepted(self, client, auth_header):
        """image/jpeg content type returns a presigned URL."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET,
                                     "S3_BUCKET": "test-bucket",
                                     "CLOUDFRONT_DOMAIN": "cdn.test.com",
                                     "AWS_ACCESS_KEY_ID": "fake-key",
                                     "AWS_SECRET_ACCESS_KEY": "fake-secret",
                                     "AWS_REGION": "us-east-1"}), \
             patch("app.routers.cms_photos.boto3") as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"

            resp = client.post(
                "/api/cms/photos/presign",
                json={"filename": "photo.jpg", "content_type": "image/jpeg"},
                headers=auth_header,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "upload_url" in data
        assert "s3_key" in data
        assert "cdn_url" in data
        assert data["s3_key"].startswith("photos/")
        assert data["s3_key"].endswith(".jpg")
        assert "cdn.test.com" in data["cdn_url"]

    def test_presign_png_accepted(self, client, auth_header):
        """image/png content type returns a presigned URL."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET,
                                     "S3_BUCKET": "test-bucket",
                                     "CLOUDFRONT_DOMAIN": "cdn.test.com",
                                     "AWS_ACCESS_KEY_ID": "fake-key",
                                     "AWS_SECRET_ACCESS_KEY": "fake-secret",
                                     "AWS_REGION": "us-east-1"}), \
             patch("app.routers.cms_photos.boto3") as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"

            resp = client.post(
                "/api/cms/photos/presign",
                json={"filename": "photo.png", "content_type": "image/png"},
                headers=auth_header,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["s3_key"].endswith(".png")

    def test_presign_invalid_content_type_rejected(self, client, auth_header):
        """Non-JPEG/PNG content types are rejected with 400."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            resp = client.post(
                "/api/cms/photos/presign",
                json={"filename": "doc.pdf", "content_type": "application/pdf"},
                headers=auth_header,
            )
        assert resp.status_code == 400

    def test_presign_gif_rejected(self, client, auth_header):
        """image/gif is not accepted."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            resp = client.post(
                "/api/cms/photos/presign",
                json={"filename": "anim.gif", "content_type": "image/gif"},
                headers=auth_header,
            )
        assert resp.status_code == 400

    def test_presign_requires_auth(self, client):
        """Presign endpoint requires authentication."""
        resp = client.post(
            "/api/cms/photos/presign",
            json={"filename": "photo.jpg", "content_type": "image/jpeg"},
        )
        assert resp.status_code in (401, 403)

    def test_note_rejects_third_photo(self, client, auth_header):
        """A note cannot have more than 2 photos (validated by schema)."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "Too many photos",
                    "body_html": "<p>Content</p>",
                    "photos": [
                        {
                            "s3_key": "photos/2024/a.jpg",
                            "cdn_url": "https://cdn.example.com/a.jpg",
                            "position": 1,
                        },
                        {
                            "s3_key": "photos/2024/b.jpg",
                            "cdn_url": "https://cdn.example.com/b.jpg",
                            "position": 2,
                        },
                        {
                            "s3_key": "photos/2024/c.jpg",
                            "cdn_url": "https://cdn.example.com/c.jpg",
                            "position": 1,
                        },
                    ],
                },
                headers=auth_header,
            )
        assert resp.status_code == 422

    def test_note_with_two_photos_then_update_to_three_rejected(
        self, client, auth_header
    ):
        """Updating a note to have 3 photos is rejected."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            # Create note with 2 photos
            create_resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "Two photos",
                    "body_html": "<p>Content</p>",
                    "photos": [
                        {
                            "s3_key": "photos/2024/a.jpg",
                            "cdn_url": "https://cdn.example.com/a.jpg",
                            "position": 1,
                        },
                        {
                            "s3_key": "photos/2024/b.jpg",
                            "cdn_url": "https://cdn.example.com/b.jpg",
                            "position": 2,
                        },
                    ],
                },
                headers=auth_header,
            )
            assert create_resp.status_code == 201
            note_id = create_resp.json()["id"]

            # Try to update with 3 photos
            update_resp = client.put(
                f"/api/cms/notes/{note_id}",
                json={
                    "photos": [
                        {
                            "s3_key": "photos/2024/x.jpg",
                            "cdn_url": "https://cdn.example.com/x.jpg",
                            "position": 1,
                        },
                        {
                            "s3_key": "photos/2024/y.jpg",
                            "cdn_url": "https://cdn.example.com/y.jpg",
                            "position": 2,
                        },
                        {
                            "s3_key": "photos/2024/z.jpg",
                            "cdn_url": "https://cdn.example.com/z.jpg",
                            "position": 1,
                        },
                    ],
                },
                headers=auth_header,
            )
        assert update_resp.status_code == 422


# ===========================================================================
# PUBLIC API INTEGRATION TESTS
# ===========================================================================


class TestPublicApiIntegration:
    """Public API: published notes appear, drafts do not; ordering."""

    def test_drafts_not_visible_in_public_list(self, client, auth_header):
        """Draft notes do not appear in the public note list."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Draft Note",
                    "body_html": "<p>This is a draft.</p>",
                    "status": "draft",
                },
                headers=auth_header,
            )
            resp = client.get("/api/notes")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    def test_published_notes_visible_in_public_list(self, client, auth_header):
        """Published notes appear in the public note list."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Published Note",
                    "body_html": "<p>This is published.</p>",
                    "status": "published",
                },
                headers=auth_header,
            )
            resp = client.get("/api/notes")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["title"] == "Published Note"

    def test_draft_not_accessible_by_id_in_public_api(self, client, auth_header):
        """Draft notes return 404 on the public detail endpoint."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            create_resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "Secret Draft",
                    "body_html": "<p>Not for public.</p>",
                    "status": "draft",
                },
                headers=auth_header,
            )
            note_id = create_resp.json()["id"]
            resp = client.get(f"/api/notes/{note_id}")
        assert resp.status_code == 404

    def test_public_list_ordered_by_published_at_desc(self, client, auth_header):
        """Public list returns notes ordered by published_at descending."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            # Create notes with explicit published_at to control order
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Oldest",
                    "body_html": "<p>Old</p>",
                    "status": "published",
                    "published_at": "2024-01-01T10:00:00Z",
                },
                headers=auth_header,
            )
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Middle",
                    "body_html": "<p>Mid</p>",
                    "status": "published",
                    "published_at": "2024-06-15T10:00:00Z",
                },
                headers=auth_header,
            )
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Newest",
                    "body_html": "<p>New</p>",
                    "status": "published",
                    "published_at": "2024-12-01T10:00:00Z",
                },
                headers=auth_header,
            )
            resp = client.get("/api/notes")

        assert resp.status_code == 200
        titles = [item["title"] for item in resp.json()["items"]]
        assert titles == ["Newest", "Middle", "Oldest"]

    def test_public_list_mixed_drafts_and_published(self, client, auth_header):
        """Only published notes appear even when drafts exist."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Draft 1",
                    "body_html": "<p>D1</p>",
                    "status": "draft",
                },
                headers=auth_header,
            )
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Published 1",
                    "body_html": "<p>P1</p>",
                    "status": "published",
                },
                headers=auth_header,
            )
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Draft 2",
                    "body_html": "<p>D2</p>",
                    "status": "draft",
                },
                headers=auth_header,
            )
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Published 2",
                    "body_html": "<p>P2</p>",
                    "status": "published",
                },
                headers=auth_header,
            )
            resp = client.get("/api/notes")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        titles = [item["title"] for item in data["items"]]
        assert "Draft 1" not in titles
        assert "Draft 2" not in titles
        assert "Published 1" in titles
        assert "Published 2" in titles

    def test_public_detail_includes_excerpt_and_labels(self, client, auth_header):
        """Public list items include excerpt and labels."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Rich Note",
                    "body_html": "<p>This is a <strong>rich</strong> note with content.</p>",
                    "status": "published",
                    "labels": ["wisdom", "life"],
                },
                headers=auth_header,
            )
            resp = client.get("/api/notes")

        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["excerpt"] == "This is a rich note with content."
        label_names = sorted([l["name"] for l in item["labels"]])
        assert label_names == ["life", "wisdom"]

    def test_public_pagination(self, client, auth_header):
        """Public list supports pagination."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            for i in range(5):
                client.post(
                    "/api/cms/notes",
                    json={
                        "title": f"Note {i}",
                        "body_html": f"<p>Body {i}</p>",
                        "status": "published",
                    },
                    headers=auth_header,
                )
            # Request page 1 with page_size 2
            resp = client.get("/api/notes?page=1&page_size=2")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) == 2


# ===========================================================================
# ISR REVALIDATION FLOW (end-to-end CMS publish flow)
# ===========================================================================


class TestIsrRevalidationFlow:
    """Verify the CMS publish flow works end-to-end.

    The ISR revalidation is a Next.js concern, but we verify that the
    backend correctly persists and exposes published notes immediately
    after the publish operation — which is what triggers the frontend
    to call the revalidation endpoint.
    """

    def test_publish_makes_note_immediately_available(self, client, auth_header):
        """After publishing, the note is immediately available via public API.

        This simulates the flow: CMS publishes → backend persists →
        frontend would call revalidate → public page shows the note.
        We verify the backend side of this contract.
        """
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            # Create as draft
            create_resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "ISR Test Note",
                    "body_html": "<p>Testing ISR flow.</p>",
                    "status": "draft",
                },
                headers=auth_header,
            )
            note_id = create_resp.json()["id"]

            # Not visible yet
            assert client.get(f"/api/notes/{note_id}").status_code == 404

            # Publish
            publish_resp = client.put(
                f"/api/cms/notes/{note_id}",
                json={"status": "published"},
                headers=auth_header,
            )
            assert publish_resp.status_code == 200
            assert publish_resp.json()["status"] == "published"

            # Immediately available in public API (no cache delay)
            detail = client.get(f"/api/notes/{note_id}")
            assert detail.status_code == 200
            assert detail.json()["title"] == "ISR Test Note"

            # Also in the list
            list_resp = client.get("/api/notes")
            assert list_resp.json()["total"] == 1

    def test_edit_published_note_reflects_immediately(self, client, auth_header):
        """Editing a published note is immediately reflected in public API."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            # Create and publish
            create_resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "Original Title",
                    "body_html": "<p>Original body.</p>",
                    "status": "published",
                },
                headers=auth_header,
            )
            note_id = create_resp.json()["id"]

            # Edit
            client.put(
                f"/api/cms/notes/{note_id}",
                json={
                    "title": "Edited Title",
                    "body_html": "<p>Edited body.</p>",
                },
                headers=auth_header,
            )

            # Public API reflects the edit immediately
            detail = client.get(f"/api/notes/{note_id}")
            assert detail.status_code == 200
            assert detail.json()["title"] == "Edited Title"
            assert detail.json()["body_html"] == "<p>Edited body.</p>"

    def test_delete_published_note_removes_immediately(self, client, auth_header):
        """Deleting a published note removes it from public API immediately."""
        with patch.dict(os.environ, {"JWT_SECRET": TEST_JWT_SECRET}):
            create_resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "To Delete",
                    "body_html": "<p>Will be deleted.</p>",
                    "status": "published",
                },
                headers=auth_header,
            )
            note_id = create_resp.json()["id"]

            # Visible
            assert client.get(f"/api/notes/{note_id}").status_code == 200

            # Delete
            client.delete(f"/api/cms/notes/{note_id}", headers=auth_header)

            # Gone
            assert client.get(f"/api/notes/{note_id}").status_code == 404
            assert client.get("/api/notes").json()["total"] == 0


# ===========================================================================
# CMS MUTATION AUTH GUARD INTEGRATION TESTS
# ===========================================================================


class TestCmsMutationAuthGuard:
    """All CMS mutation endpoints reject requests without valid JWT."""

    def test_create_note_requires_auth(self, client):
        resp = client.post(
            "/api/cms/notes",
            json={"title": "No Auth", "body_html": "<p>X</p>"},
        )
        assert resp.status_code in (401, 403)

    def test_update_note_requires_auth(self, client):
        resp = client.put(
            "/api/cms/notes/1",
            json={"title": "No Auth"},
        )
        assert resp.status_code in (401, 403)

    def test_delete_note_requires_auth(self, client):
        resp = client.delete("/api/cms/notes/1")
        assert resp.status_code in (401, 403)

    def test_list_cms_notes_requires_auth(self, client):
        resp = client.get("/api/cms/notes")
        assert resp.status_code in (401, 403)

    def test_get_cms_note_requires_auth(self, client):
        resp = client.get("/api/cms/notes/1")
        assert resp.status_code in (401, 403)

    def test_photo_presign_requires_auth(self, client):
        resp = client.post(
            "/api/cms/photos/presign",
            json={"filename": "x.jpg", "content_type": "image/jpeg"},
        )
        assert resp.status_code in (401, 403)

    def test_photo_delete_requires_auth(self, client):
        resp = client.delete("/api/cms/photos/photos/2024/x.jpg")
        assert resp.status_code in (401, 403)
