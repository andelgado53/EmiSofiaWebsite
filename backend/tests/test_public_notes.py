"""Tests for the public GET /api/notes endpoint."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Note, Label, NoteLabel, Photo


# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared&uri=true"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _create_published_note(
    db,
    title: str = "Test Note",
    body_html: str = "<p>Hello world</p>",
    published_at: datetime | None = None,
    created_at: datetime | None = None,
    labels: list[str] | None = None,
) -> Note:
    """Insert a published note into the test database."""
    now = datetime.now(timezone.utc)
    note = Note(
        title=title,
        body_html=body_html,
        status="published",
        published_at=published_at or now,
        created_at=created_at or now,
        updated_at=now,
    )
    db.add(note)
    db.flush()

    if labels:
        for label_name in labels:
            label = db.query(Label).filter(Label.name == label_name).first()
            if not label:
                label = Label(name=label_name)
                db.add(label)
                db.flush()
            db.add(NoteLabel(note_id=note.id, label_id=label.id))

    db.commit()
    db.refresh(note)
    return note


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListNotesEndpoint:
    def test_returns_empty_list_when_no_notes(self, client):
        response = client.get("/api/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["items"] == []

    def test_returns_published_notes_only(self, client, db):
        # Create one published and one draft note
        _create_published_note(db, title="Published Note")
        draft = Note(
            title="Draft Note",
            body_html="<p>Draft</p>",
            status="draft",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(draft)
        db.commit()

        response = client.get("/api/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Published Note"

    def test_orders_by_published_at_desc(self, client, db):
        now = datetime.now(timezone.utc)
        _create_published_note(db, title="Older", published_at=now - timedelta(days=2))
        _create_published_note(db, title="Newer", published_at=now - timedelta(days=1))
        _create_published_note(db, title="Newest", published_at=now)

        response = client.get("/api/notes")
        data = response.json()
        titles = [item["title"] for item in data["items"]]
        assert titles == ["Newest", "Newer", "Older"]

    def test_breaks_ties_by_created_at_desc(self, client, db):
        same_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        _create_published_note(
            db,
            title="Created First",
            published_at=same_time,
            created_at=same_time - timedelta(hours=2),
        )
        _create_published_note(
            db,
            title="Created Second",
            published_at=same_time,
            created_at=same_time - timedelta(hours=1),
        )

        response = client.get("/api/notes")
        data = response.json()
        titles = [item["title"] for item in data["items"]]
        assert titles == ["Created Second", "Created First"]

    def test_pagination_defaults(self, client, db):
        # Create 25 notes
        now = datetime.now(timezone.utc)
        for i in range(25):
            _create_published_note(
                db,
                title=f"Note {i}",
                published_at=now - timedelta(hours=i),
            )

        response = client.get("/api/notes")
        data = response.json()
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 20

    def test_pagination_page_2(self, client, db):
        now = datetime.now(timezone.utc)
        for i in range(25):
            _create_published_note(
                db,
                title=f"Note {i}",
                published_at=now - timedelta(hours=i),
            )

        response = client.get("/api/notes?page=2")
        data = response.json()
        assert data["total"] == 25
        assert data["page"] == 2
        assert len(data["items"]) == 5

    def test_custom_page_size(self, client, db):
        now = datetime.now(timezone.utc)
        for i in range(10):
            _create_published_note(
                db,
                title=f"Note {i}",
                published_at=now - timedelta(hours=i),
            )

        response = client.get("/api/notes?page_size=5")
        data = response.json()
        assert data["page_size"] == 5
        assert len(data["items"]) == 5

    def test_page_size_max_50(self, client):
        response = client.get("/api/notes?page_size=100")
        assert response.status_code == 422  # Validation error

    def test_page_size_min_1(self, client):
        response = client.get("/api/notes?page_size=0")
        assert response.status_code == 422

    def test_page_min_1(self, client):
        response = client.get("/api/notes?page=0")
        assert response.status_code == 422

    def test_excerpt_generated_from_body(self, client, db):
        _create_published_note(
            db,
            title="With Body",
            body_html="<p>This is a <strong>test</strong> note body.</p>",
        )

        response = client.get("/api/notes")
        data = response.json()
        assert data["items"][0]["excerpt"] == "This is a test note body."

    def test_excerpt_truncated_to_200_chars(self, client, db):
        long_text = "A" * 300
        _create_published_note(
            db,
            title="Long Body",
            body_html=f"<p>{long_text}</p>",
        )

        response = client.get("/api/notes")
        data = response.json()
        assert len(data["items"][0]["excerpt"]) == 200

    def test_labels_included_in_response(self, client, db):
        _create_published_note(
            db,
            title="Labelled Note",
            labels=["life", "lessons"],
        )

        response = client.get("/api/notes")
        data = response.json()
        label_names = [l["name"] for l in data["items"][0]["labels"]]
        assert "life" in label_names
        assert "lessons" in label_names

    def test_response_item_has_required_fields(self, client, db):
        _create_published_note(db, title="Complete Note", labels=["tag1"])

        response = client.get("/api/notes")
        data = response.json()
        item = data["items"][0]
        assert "id" in item
        assert "title" in item
        assert "excerpt" in item
        assert "published_at" in item
        assert "labels" in item


class TestGetNoteDetailEndpoint:
    def test_returns_published_note(self, client, db):
        note = _create_published_note(db, title="Detail Note", body_html="<p>Full body</p>")

        response = client.get(f"/api/notes/{note.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == note.id
        assert data["title"] == "Detail Note"
        assert data["body_html"] == "<p>Full body</p>"
        assert "published_at" in data
        assert data["labels"] == []
        assert data["photos"] == []

    def test_returns_404_for_nonexistent_note(self, client):
        response = client.get("/api/notes/9999")
        assert response.status_code == 404

    def test_returns_404_for_draft_note(self, client, db):
        now = datetime.now(timezone.utc)
        draft = Note(
            title="Draft Note",
            body_html="<p>Draft</p>",
            status="draft",
            created_at=now,
            updated_at=now,
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        response = client.get(f"/api/notes/{draft.id}")
        assert response.status_code == 404

    def test_includes_labels(self, client, db):
        note = _create_published_note(db, title="Labelled", labels=["life", "lessons"])

        response = client.get(f"/api/notes/{note.id}")
        assert response.status_code == 200
        data = response.json()
        label_names = [l["name"] for l in data["labels"]]
        assert "life" in label_names
        assert "lessons" in label_names

    def test_includes_photos_ordered_by_position(self, client, db):
        note = _create_published_note(db, title="With Photos")

        # Add photos in reverse position order
        photo2 = Photo(
            note_id=note.id,
            s3_key="photos/2024/photo2.jpg",
            cdn_url="https://cdn.example.com/photos/2024/photo2.jpg",
            position=2,
        )
        photo1 = Photo(
            note_id=note.id,
            s3_key="photos/2024/photo1.jpg",
            cdn_url="https://cdn.example.com/photos/2024/photo1.jpg",
            position=1,
        )
        db.add(photo2)
        db.add(photo1)
        db.commit()

        response = client.get(f"/api/notes/{note.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["photos"]) == 2
        assert data["photos"][0]["position"] == 1
        assert data["photos"][0]["cdn_url"] == "https://cdn.example.com/photos/2024/photo1.jpg"
        assert data["photos"][1]["position"] == 2
        assert data["photos"][1]["cdn_url"] == "https://cdn.example.com/photos/2024/photo2.jpg"

    def test_response_has_all_required_fields(self, client, db):
        note = _create_published_note(
            db, title="Complete", body_html="<p>Body</p>", labels=["tag"]
        )
        photo = Photo(
            note_id=note.id,
            s3_key="photos/2024/img.png",
            cdn_url="https://cdn.example.com/photos/2024/img.png",
            position=1,
        )
        db.add(photo)
        db.commit()

        response = client.get(f"/api/notes/{note.id}")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert "body_html" in data
        assert "published_at" in data
        assert "labels" in data
        assert "photos" in data
