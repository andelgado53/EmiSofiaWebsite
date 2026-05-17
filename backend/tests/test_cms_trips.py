"""Tests for the CMS trips router."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_author
from app.database import Base, get_db
from app.main import app
from app.models import Trip, TripPhoto

# In-memory SQLite for tests
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Mock auth to always succeed
def override_get_current_author():
    return {"sub": "author"}


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_author] = override_get_current_author
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    return TestClient(app)


class TestCreateTrip:
    def test_create_draft_trip(self, client):
        response = client.post(
            "/api/cms/trips",
            json={
                "title": "Beach Day",
                "trip_date": "2025-07-15",
                "description": "A wonderful day at the beach",
                "status": "draft",
                "photos": [],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Beach Day"
        assert data["trip_date"] == "2025-07-15"
        assert data["description"] == "A wonderful day at the beach"
        assert data["status"] == "draft"
        assert data["published_at"] is None
        assert data["photos"] == []

    def test_create_published_trip_sets_published_at(self, client):
        response = client.post(
            "/api/cms/trips",
            json={
                "title": "Mountain Hike",
                "trip_date": "2025-06-01",
                "status": "published",
                "photos": [],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None

    def test_create_trip_with_photos(self, client):
        response = client.post(
            "/api/cms/trips",
            json={
                "title": "Park Visit",
                "trip_date": "2025-05-20",
                "status": "draft",
                "photos": [
                    {
                        "s3_key": "photos/2025/abc.jpg",
                        "cdn_url": "https://cdn.example.com/photos/2025/abc.jpg",
                        "position": 1,
                    },
                    {
                        "s3_key": "photos/2025/def.jpg",
                        "cdn_url": "https://cdn.example.com/photos/2025/def.jpg",
                        "position": 2,
                    },
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["photos"]) == 2
        assert data["photos"][0]["position"] == 1
        assert data["photos"][1]["position"] == 2

    def test_create_trip_title_required(self, client):
        response = client.post(
            "/api/cms/trips",
            json={
                "title": "",
                "trip_date": "2025-07-15",
                "status": "draft",
                "photos": [],
            },
        )
        assert response.status_code == 422

    def test_create_trip_title_too_long(self, client):
        response = client.post(
            "/api/cms/trips",
            json={
                "title": "x" * 151,
                "trip_date": "2025-07-15",
                "status": "draft",
                "photos": [],
            },
        )
        assert response.status_code == 422

    def test_create_trip_description_too_long(self, client):
        response = client.post(
            "/api/cms/trips",
            json={
                "title": "Valid Title",
                "trip_date": "2025-07-15",
                "description": "x" * 2001,
                "status": "draft",
                "photos": [],
            },
        )
        assert response.status_code == 422


class TestListTrips:
    def test_list_empty(self, client):
        response = client.get("/api/cms/trips")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_includes_drafts_and_published(self, client):
        # Create a draft
        client.post(
            "/api/cms/trips",
            json={
                "title": "Draft Trip",
                "trip_date": "2025-01-01",
                "status": "draft",
                "photos": [],
            },
        )
        # Create a published trip
        client.post(
            "/api/cms/trips",
            json={
                "title": "Published Trip",
                "trip_date": "2025-02-01",
                "status": "published",
                "photos": [],
            },
        )

        response = client.get("/api/cms/trips")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestGetTrip:
    def test_get_existing_trip(self, client):
        create_resp = client.post(
            "/api/cms/trips",
            json={
                "title": "My Trip",
                "trip_date": "2025-03-15",
                "status": "draft",
                "photos": [],
            },
        )
        trip_id = create_resp.json()["id"]

        response = client.get(f"/api/cms/trips/{trip_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "My Trip"

    def test_get_nonexistent_trip(self, client):
        response = client.get("/api/cms/trips/9999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Trip not found"


class TestUpdateTrip:
    def test_update_title(self, client):
        create_resp = client.post(
            "/api/cms/trips",
            json={
                "title": "Original",
                "trip_date": "2025-04-01",
                "status": "draft",
                "photos": [],
            },
        )
        trip_id = create_resp.json()["id"]

        response = client.put(
            f"/api/cms/trips/{trip_id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_status_to_published_sets_published_at(self, client):
        create_resp = client.post(
            "/api/cms/trips",
            json={
                "title": "Draft Trip",
                "trip_date": "2025-04-01",
                "status": "draft",
                "photos": [],
            },
        )
        trip_id = create_resp.json()["id"]
        assert create_resp.json()["published_at"] is None

        response = client.put(
            f"/api/cms/trips/{trip_id}",
            json={"status": "published"},
        )
        assert response.status_code == 200
        assert response.json()["published_at"] is not None

    @patch("app.routers.cms_trips._get_s3_client")
    def test_update_photos_deletes_removed_from_s3(self, mock_s3_factory, client):
        mock_client = MagicMock()
        mock_s3_factory.return_value = mock_client

        create_resp = client.post(
            "/api/cms/trips",
            json={
                "title": "Photo Trip",
                "trip_date": "2025-04-01",
                "status": "draft",
                "photos": [
                    {
                        "s3_key": "photos/2025/old.jpg",
                        "cdn_url": "https://cdn.example.com/photos/2025/old.jpg",
                        "position": 1,
                    },
                ],
            },
        )
        trip_id = create_resp.json()["id"]

        # Update with different photos — old one should be deleted from S3
        response = client.put(
            f"/api/cms/trips/{trip_id}",
            json={
                "photos": [
                    {
                        "s3_key": "photos/2025/new.jpg",
                        "cdn_url": "https://cdn.example.com/photos/2025/new.jpg",
                        "position": 1,
                    },
                ],
            },
        )
        assert response.status_code == 200
        assert len(response.json()["photos"]) == 1
        assert response.json()["photos"][0]["cdn_url"] == "https://cdn.example.com/photos/2025/new.jpg"

        # Verify S3 delete was called for the removed photo
        mock_client.delete_object.assert_called_once()

    def test_update_nonexistent_trip(self, client):
        response = client.put(
            "/api/cms/trips/9999",
            json={"title": "Nope"},
        )
        assert response.status_code == 404


class TestDeleteTrip:
    @patch("app.routers.cms_trips._get_s3_client")
    def test_delete_trip_with_photos(self, mock_s3_factory, client):
        mock_client = MagicMock()
        mock_s3_factory.return_value = mock_client

        create_resp = client.post(
            "/api/cms/trips",
            json={
                "title": "To Delete",
                "trip_date": "2025-05-01",
                "status": "draft",
                "photos": [
                    {
                        "s3_key": "photos/2025/del1.jpg",
                        "cdn_url": "https://cdn.example.com/photos/2025/del1.jpg",
                        "position": 1,
                    },
                    {
                        "s3_key": "photos/2025/del2.jpg",
                        "cdn_url": "https://cdn.example.com/photos/2025/del2.jpg",
                        "position": 2,
                    },
                ],
            },
        )
        trip_id = create_resp.json()["id"]

        response = client.delete(f"/api/cms/trips/{trip_id}")
        assert response.status_code == 204

        # Verify S3 delete was called for each photo
        assert mock_client.delete_object.call_count == 2

        # Verify trip is gone
        get_resp = client.get(f"/api/cms/trips/{trip_id}")
        assert get_resp.status_code == 404

    def test_delete_trip_without_photos(self, client):
        create_resp = client.post(
            "/api/cms/trips",
            json={
                "title": "No Photos",
                "trip_date": "2025-05-01",
                "status": "draft",
                "photos": [],
            },
        )
        trip_id = create_resp.json()["id"]

        response = client.delete(f"/api/cms/trips/{trip_id}")
        assert response.status_code == 204

    def test_delete_nonexistent_trip(self, client):
        response = client.delete("/api/cms/trips/9999")
        assert response.status_code == 404
