"""Unit tests for POST /api/cms/notes endpoint."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token
from app.config import settings
from app.database import Base, get_db
from app.models import Label, Note, NoteLabel, Photo
from app.main import app


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
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_header():
    """Return a valid Authorization header for CMS endpoints."""
    with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
        token = create_access_token(sub="author")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/cms/notes
# ---------------------------------------------------------------------------


class TestCreateNote:
    def test_create_minimal_draft(self, client, auth_header):
        """Create a draft note with just title and body."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/notes",
                json={
                    "title": "Hello Emi",
                    "body_html": "<p>First note</p>",
                },
                headers=auth_header,
            )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Hello Emi"
        assert data["body_html"] == "<p>First note</p>"
        assert data["labels"] == []
        assert data["photos"] == []
        # Draft should not have published_at set automatically
        assert data["published_at"] is None

    def test_create_published_note_sets_published_at(self, client, auth_header):
        """When status is 'published' and published_at is null, set it to now."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/notes",
                json={
                    "title": "Published note",
                    "body_html": "<p>Content</p>",
                    "status": "published",
                },
                headers=auth_header,
            )
        assert response.status_code == 201
        data = response.json()
        assert data["published_at"] is not None

    def test_create_published_note_preserves_explicit_published_at(
        self, client, auth_header
    ):
        """When published_at is explicitly provided, use it."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/notes",
                json={
                    "title": "Backdated note",
                    "body_html": "<p>Content</p>",
                    "status": "published",
                    "published_at": "2024-01-15T10:00:00Z",
                },
                headers=auth_header,
            )
        assert response.status_code == 201
        data = response.json()
        assert "2024-01-15" in data["published_at"]

    def test_create_note_with_labels(self, client, auth_header):
        """Labels are normalised and associated with the note."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/notes",
                json={
                    "title": "Labelled note",
                    "body_html": "<p>Content</p>",
                    "labels": ["Life", " lessons ", "LIFE"],
                },
                headers=auth_header,
            )
        assert response.status_code == 201
        data = response.json()
        label_names = [lbl["name"] for lbl in data["labels"]]
        # "Life" and "LIFE" should be deduplicated to "life"
        assert "life" in label_names
        assert "lessons" in label_names
        assert len(label_names) == 2

    def test_create_note_with_photos(self, client, auth_header):
        """Photos are created and returned in position order."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/notes",
                json={
                    "title": "Photo note",
                    "body_html": "<p>Content</p>",
                    "photos": [
                        {
                            "s3_key": "photos/2024/abc.jpg",
                            "cdn_url": "https://cdn.example.com/photos/2024/abc.jpg",
                            "position": 2,
                        },
                        {
                            "s3_key": "photos/2024/def.jpg",
                            "cdn_url": "https://cdn.example.com/photos/2024/def.jpg",
                            "position": 1,
                        },
                    ],
                },
                headers=auth_header,
            )
        assert response.status_code == 201
        data = response.json()
        assert len(data["photos"]) == 2
        # Photos should be ordered by position ascending
        assert data["photos"][0]["position"] == 1
        assert data["photos"][1]["position"] == 2

    def test_create_note_sanitises_html(self, client, auth_header):
        """Dangerous HTML tags are stripped from body_html."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/notes",
                json={
                    "title": "Sanitised note",
                    "body_html": '<p>Hello</p><script>alert("xss")</script>',
                },
                headers=auth_header,
            )
        assert response.status_code == 201
        data = response.json()
        assert "<script>" not in data["body_html"]
        assert "<p>Hello</p>" in data["body_html"]

    def test_create_note_requires_auth(self, client):
        """Endpoint returns 401 without a valid token."""
        response = client.post(
            "/api/cms/notes",
            json={
                "title": "Unauthorized",
                "body_html": "<p>Content</p>",
            },
        )
        assert response.status_code == 403 or response.status_code == 401

    def test_create_note_rejects_invalid_title(self, client, auth_header):
        """Empty title is rejected with 422."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.post(
                "/api/cms/notes",
                json={
                    "title": "",
                    "body_html": "<p>Content</p>",
                },
                headers=auth_header,
            )
        assert response.status_code == 422

    def test_label_upsert_reuses_existing_labels(self, client, auth_header):
        """Creating two notes with the same label reuses the Label record."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            # Create first note with label "life"
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Note 1",
                    "body_html": "<p>First</p>",
                    "labels": ["life"],
                },
                headers=auth_header,
            )
            # Create second note with same label
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Note 2",
                    "body_html": "<p>Second</p>",
                    "labels": ["life"],
                },
                headers=auth_header,
            )

        # Verify only one Label record exists
        db = TestSessionLocal()
        labels = db.query(Label).all()
        assert len(labels) == 1
        assert labels[0].name == "life"
        db.close()


# ---------------------------------------------------------------------------
# GET /api/cms/notes
# ---------------------------------------------------------------------------


class TestListNotes:
    def test_list_notes_empty(self, client, auth_header):
        """Returns an empty list when no notes exist."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.get("/api/cms/notes", headers=auth_header)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_notes_includes_drafts_and_published(self, client, auth_header):
        """Both draft and published notes are returned."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            # Create a draft
            client.post(
                "/api/cms/notes",
                json={"title": "Draft note", "body_html": "<p>Draft</p>"},
                headers=auth_header,
            )
            # Create a published note
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Published note",
                    "body_html": "<p>Published</p>",
                    "status": "published",
                },
                headers=auth_header,
            )
            response = client.get("/api/cms/notes", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        statuses = {note["status"] for note in data}
        assert "draft" in statuses
        assert "published" in statuses

    def test_list_notes_ordered_by_created_at_desc(self, client, auth_header):
        """Notes are returned newest first (by created_at)."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            client.post(
                "/api/cms/notes",
                json={"title": "First", "body_html": "<p>1</p>"},
                headers=auth_header,
            )
            client.post(
                "/api/cms/notes",
                json={"title": "Second", "body_html": "<p>2</p>"},
                headers=auth_header,
            )
            client.post(
                "/api/cms/notes",
                json={"title": "Third", "body_html": "<p>3</p>"},
                headers=auth_header,
            )
            response = client.get("/api/cms/notes", headers=auth_header)

        data = response.json()
        assert data[0]["title"] == "Third"
        assert data[1]["title"] == "Second"
        assert data[2]["title"] == "First"

    def test_list_notes_requires_auth(self, client):
        """Endpoint returns 401/403 without a valid token."""
        response = client.get("/api/cms/notes")
        assert response.status_code in (401, 403)

    def test_list_notes_includes_labels_and_photos(self, client, auth_header):
        """Response includes labels and photos for each note."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            client.post(
                "/api/cms/notes",
                json={
                    "title": "Full note",
                    "body_html": "<p>Content</p>",
                    "labels": ["life", "lessons"],
                    "photos": [
                        {
                            "s3_key": "photos/2024/a.jpg",
                            "cdn_url": "https://cdn.example.com/a.jpg",
                            "position": 1,
                        }
                    ],
                },
                headers=auth_header,
            )
            response = client.get("/api/cms/notes", headers=auth_header)

        data = response.json()
        assert len(data) == 1
        note = data[0]
        assert len(note["labels"]) == 2
        assert len(note["photos"]) == 1


# ---------------------------------------------------------------------------
# GET /api/cms/notes/{id}
# ---------------------------------------------------------------------------


class TestGetNote:
    def test_get_draft_note(self, client, auth_header):
        """Can retrieve a draft note by ID."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            create_resp = client.post(
                "/api/cms/notes",
                json={"title": "My Draft", "body_html": "<p>Draft body</p>"},
                headers=auth_header,
            )
            note_id = create_resp.json()["id"]
            response = client.get(f"/api/cms/notes/{note_id}", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == note_id
        assert data["title"] == "My Draft"
        assert data["status"] == "draft"

    def test_get_published_note(self, client, auth_header):
        """Can retrieve a published note by ID."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            create_resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "Published",
                    "body_html": "<p>Body</p>",
                    "status": "published",
                },
                headers=auth_header,
            )
            note_id = create_resp.json()["id"]
            response = client.get(f"/api/cms/notes/{note_id}", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None

    def test_get_note_not_found(self, client, auth_header):
        """Returns 404 for a non-existent note ID."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.get("/api/cms/notes/9999", headers=auth_header)
        assert response.status_code == 404

    def test_get_note_requires_auth(self, client):
        """Endpoint returns 401/403 without a valid token."""
        response = client.get("/api/cms/notes/1")
        assert response.status_code in (401, 403)

    def test_get_note_includes_all_fields(self, client, auth_header):
        """Response includes labels, photos, status, and published_at."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            create_resp = client.post(
                "/api/cms/notes",
                json={
                    "title": "Full note",
                    "body_html": "<p>Content</p>",
                    "status": "published",
                    "labels": ["tag1"],
                    "photos": [
                        {
                            "s3_key": "photos/2024/x.jpg",
                            "cdn_url": "https://cdn.example.com/x.jpg",
                            "position": 1,
                        }
                    ],
                },
                headers=auth_header,
            )
            note_id = create_resp.json()["id"]
            response = client.get(f"/api/cms/notes/{note_id}", headers=auth_header)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Full note"
        assert data["body_html"] == "<p>Content</p>"
        assert data["status"] == "published"
        assert data["published_at"] is not None
        assert len(data["labels"]) == 1
        assert data["labels"][0]["name"] == "tag1"
        assert len(data["photos"]) == 1
        assert data["photos"][0]["cdn_url"] == "https://cdn.example.com/x.jpg"


# ---------------------------------------------------------------------------
# PUT /api/cms/notes/{id}
# ---------------------------------------------------------------------------


class TestUpdateNote:
    def _create_note(self, client, auth_header, **kwargs):
        """Helper to create a note and return its ID."""
        payload = {"title": "Original", "body_html": "<p>Original body</p>"}
        payload.update(kwargs)
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            resp = client.post("/api/cms/notes", json=payload, headers=auth_header)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_update_title(self, client, auth_header):
        """Updating only the title leaves other fields unchanged."""
        note_id = self._create_note(client, auth_header)
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={"title": "Updated Title"},
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["body_html"] == "<p>Original body</p>"

    def test_update_body_html_sanitises(self, client, auth_header):
        """body_html is sanitised on update."""
        note_id = self._create_note(client, auth_header)
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={"body_html": '<p>Safe</p><script>alert("xss")</script>'},
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        assert "<script>" not in data["body_html"]
        assert "<p>Safe</p>" in data["body_html"]

    def test_update_labels_replaces_existing(self, client, auth_header):
        """Providing labels fully replaces the existing label set."""
        note_id = self._create_note(
            client, auth_header, labels=["old-label", "another"]
        )
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={"labels": ["new-label"]},
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        label_names = [lbl["name"] for lbl in data["labels"]]
        assert label_names == ["new-label"]

    def test_update_labels_empty_list_removes_all(self, client, auth_header):
        """Providing an empty labels list removes all labels."""
        note_id = self._create_note(client, auth_header, labels=["tag1", "tag2"])
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={"labels": []},
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["labels"] == []

    def test_update_photos_replaces_existing(self, client, auth_header):
        """Providing photos fully replaces the existing photo set."""
        note_id = self._create_note(
            client,
            auth_header,
            photos=[
                {
                    "s3_key": "photos/2024/old.jpg",
                    "cdn_url": "https://cdn.example.com/old.jpg",
                    "position": 1,
                }
            ],
        )
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={
                    "photos": [
                        {
                            "s3_key": "photos/2024/new.jpg",
                            "cdn_url": "https://cdn.example.com/new.jpg",
                            "position": 2,
                        }
                    ]
                },
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        assert len(data["photos"]) == 1
        assert data["photos"][0]["cdn_url"] == "https://cdn.example.com/new.jpg"
        assert data["photos"][0]["position"] == 2

    def test_update_draft_to_published_sets_published_at(self, client, auth_header):
        """Transitioning from draft to published sets published_at automatically."""
        note_id = self._create_note(client, auth_header)  # default is draft
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={"status": "published"},
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None

    def test_update_published_note_preserves_published_at(self, client, auth_header):
        """Updating a published note without changing status preserves published_at."""
        note_id = self._create_note(client, auth_header, status="published")
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            get_resp = client.get(f"/api/cms/notes/{note_id}", headers=auth_header)
            original_published_at = get_resp.json()["published_at"]

            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={"title": "New title"},
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["published_at"] == original_published_at

    def test_update_not_found(self, client, auth_header):
        """Returns 404 for a non-existent note ID."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                "/api/cms/notes/9999",
                json={"title": "Nope"},
                headers=auth_header,
            )
        assert response.status_code == 404

    def test_update_requires_auth(self, client):
        """Endpoint returns 401/403 without a valid token."""
        response = client.put(
            "/api/cms/notes/1",
            json={"title": "Unauthorized"},
        )
        assert response.status_code in (401, 403)

    def test_update_labels_normalises_and_deduplicates(self, client, auth_header):
        """Labels are normalised and deduplicated on update."""
        note_id = self._create_note(client, auth_header)
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={"labels": ["Life", " LIFE ", "lessons"]},
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        label_names = [lbl["name"] for lbl in data["labels"]]
        assert "life" in label_names
        assert "lessons" in label_names
        assert len(label_names) == 2

    def test_update_omitted_labels_preserves_existing(self, client, auth_header):
        """When labels is not provided (None), existing labels are preserved."""
        note_id = self._create_note(client, auth_header, labels=["keep-me"])
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.put(
                f"/api/cms/notes/{note_id}",
                json={"title": "New title only"},
                headers=auth_header,
            )
        assert response.status_code == 200
        data = response.json()
        label_names = [lbl["name"] for lbl in data["labels"]]
        assert "keep-me" in label_names


# ---------------------------------------------------------------------------
# DELETE /api/cms/notes/{id}
# ---------------------------------------------------------------------------


class TestDeleteNote:
    def _create_note(self, client, auth_header, **kwargs):
        """Helper to create a note and return its ID."""
        payload = {"title": "To Delete", "body_html": "<p>Body</p>"}
        payload.update(kwargs)
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            resp = client.post("/api/cms/notes", json=payload, headers=auth_header)
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_delete_note_returns_204(self, client, auth_header):
        """Deleting an existing note returns 204 No Content."""
        note_id = self._create_note(client, auth_header)
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.delete(f"/api/cms/notes/{note_id}", headers=auth_header)
        assert response.status_code == 204

    def test_delete_note_removes_from_db(self, client, auth_header):
        """After deletion, the note is no longer retrievable."""
        note_id = self._create_note(client, auth_header)
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            client.delete(f"/api/cms/notes/{note_id}", headers=auth_header)
            response = client.get(f"/api/cms/notes/{note_id}", headers=auth_header)
        assert response.status_code == 404

    def test_delete_note_cascades_labels(self, client, auth_header):
        """Deleting a note removes its NoteLabel associations."""
        note_id = self._create_note(client, auth_header, labels=["tag1", "tag2"])
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            client.delete(f"/api/cms/notes/{note_id}", headers=auth_header)

        # Verify NoteLabel rows are gone
        db = TestSessionLocal()
        note_labels = db.query(NoteLabel).filter(NoteLabel.note_id == note_id).all()
        assert len(note_labels) == 0
        db.close()

    def test_delete_note_cascades_photos(self, client, auth_header):
        """Deleting a note removes its Photo records."""
        note_id = self._create_note(
            client,
            auth_header,
            photos=[
                {
                    "s3_key": "photos/2024/del.jpg",
                    "cdn_url": "https://cdn.example.com/del.jpg",
                    "position": 1,
                }
            ],
        )
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            client.delete(f"/api/cms/notes/{note_id}", headers=auth_header)

        # Verify Photo rows are gone
        db = TestSessionLocal()
        photos = db.query(Photo).filter(Photo.note_id == note_id).all()
        assert len(photos) == 0
        db.close()

    def test_delete_note_not_found(self, client, auth_header):
        """Returns 404 for a non-existent note ID."""
        with patch.dict(os.environ, {"JWT_SECRET": "test-secret"}):
            response = client.delete("/api/cms/notes/9999", headers=auth_header)
        assert response.status_code == 404

    def test_delete_note_requires_auth(self, client):
        """Endpoint returns 401/403 without a valid token."""
        response = client.delete("/api/cms/notes/1")
        assert response.status_code in (401, 403)
