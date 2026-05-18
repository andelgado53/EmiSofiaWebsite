"""Tests for the public art API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import ArtPiece


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


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
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


def _create_art_piece(
    db,
    year: int = 2024,
    title: str | None = None,
    position: int = 1,
    status: str = "published",
    cdn_url: str | None = None,
) -> ArtPiece:
    """Insert an art piece into the test database."""
    now = datetime.now(timezone.utc)
    piece = ArtPiece(
        year=year,
        title=title,
        s3_key=f"photos/{year}/piece_{position}.jpg",
        cdn_url=cdn_url or f"https://cdn.example.com/photos/{year}/piece_{position}.jpg",
        position=position,
        status=status,
        published_at=now if status == "published" else None,
        created_at=now,
        updated_at=now,
    )
    db.add(piece)
    db.commit()
    db.refresh(piece)
    return piece


# ---------------------------------------------------------------------------
# Tests: GET /api/art/years
# ---------------------------------------------------------------------------


class TestListYears:
    def test_returns_empty_list_when_no_art(self, client):
        response = client.get("/api/art/years")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_only_years_with_published_pieces(self, client, db):
        _create_art_piece(db, year=2024, status="published", position=1)
        _create_art_piece(db, year=2023, status="draft", position=1)

        response = client.get("/api/art/years")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["year"] == 2024

    def test_years_ordered_newest_first(self, client, db):
        _create_art_piece(db, year=2022, status="published", position=1)
        _create_art_piece(db, year=2024, status="published", position=1)
        _create_art_piece(db, year=2023, status="published", position=1)

        response = client.get("/api/art/years")
        data = response.json()
        years = [item["year"] for item in data]
        assert years == [2024, 2023, 2022]

    def test_cover_photo_is_lowest_position_published_piece(self, client, db):
        _create_art_piece(
            db, year=2024, position=2, status="published",
            cdn_url="https://cdn.example.com/pos2.jpg",
        )
        _create_art_piece(
            db, year=2024, position=1, status="published",
            cdn_url="https://cdn.example.com/pos1.jpg",
        )
        _create_art_piece(
            db, year=2024, position=3, status="published",
            cdn_url="https://cdn.example.com/pos3.jpg",
        )

        response = client.get("/api/art/years")
        data = response.json()
        assert data[0]["cover_photo_url"] == "https://cdn.example.com/pos1.jpg"

    def test_cover_photo_ignores_draft_pieces(self, client, db):
        # Draft piece at position 1 should not be the cover
        _create_art_piece(
            db, year=2024, position=1, status="draft",
            cdn_url="https://cdn.example.com/draft.jpg",
        )
        _create_art_piece(
            db, year=2024, position=2, status="published",
            cdn_url="https://cdn.example.com/published.jpg",
        )

        response = client.get("/api/art/years")
        data = response.json()
        assert data[0]["cover_photo_url"] == "https://cdn.example.com/published.jpg"

    def test_count_reflects_published_pieces_only(self, client, db):
        _create_art_piece(db, year=2024, position=1, status="published")
        _create_art_piece(db, year=2024, position=2, status="published")
        _create_art_piece(db, year=2024, position=3, status="draft")

        response = client.get("/api/art/years")
        data = response.json()
        assert data[0]["count"] == 2

    def test_year_summary_has_required_fields(self, client, db):
        _create_art_piece(db, year=2024, position=1, status="published")

        response = client.get("/api/art/years")
        data = response.json()
        item = data[0]
        assert "year" in item
        assert "cover_photo_url" in item
        assert "count" in item


# ---------------------------------------------------------------------------
# Tests: GET /api/art/years/{year}
# ---------------------------------------------------------------------------


class TestGetYearGallery:
    def test_returns_empty_list_for_year_with_no_published_pieces(self, client):
        response = client.get("/api/art/years/2024")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_only_published_pieces(self, client, db):
        _create_art_piece(db, year=2024, position=1, status="published", title="Pub")
        _create_art_piece(db, year=2024, position=2, status="draft", title="Draft")

        response = client.get("/api/art/years/2024")
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Pub"

    def test_pieces_ordered_by_position_ascending(self, client, db):
        _create_art_piece(db, year=2024, position=3, status="published", title="Third")
        _create_art_piece(db, year=2024, position=1, status="published", title="First")
        _create_art_piece(db, year=2024, position=2, status="published", title="Second")

        response = client.get("/api/art/years/2024")
        data = response.json()
        titles = [p["title"] for p in data]
        assert titles == ["First", "Second", "Third"]

    def test_does_not_include_pieces_from_other_years(self, client, db):
        _create_art_piece(db, year=2024, position=1, status="published", title="2024 piece")
        _create_art_piece(db, year=2023, position=1, status="published", title="2023 piece")

        response = client.get("/api/art/years/2024")
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "2024 piece"

    def test_piece_has_required_fields(self, client, db):
        _create_art_piece(
            db, year=2024, position=1, status="published",
            title="Butterfly", cdn_url="https://cdn.example.com/art.jpg",
        )

        response = client.get("/api/art/years/2024")
        data = response.json()
        piece = data[0]
        assert "id" in piece
        assert piece["cdn_url"] == "https://cdn.example.com/art.jpg"
        assert piece["title"] == "Butterfly"
        assert piece["position"] == 1

    def test_piece_with_no_title_returns_null(self, client, db):
        _create_art_piece(db, year=2024, position=1, status="published", title=None)

        response = client.get("/api/art/years/2024")
        data = response.json()
        assert data[0]["title"] is None
