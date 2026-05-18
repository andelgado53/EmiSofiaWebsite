"""Pydantic v2 schemas for the Notes for Emi API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Nested schemas
# ---------------------------------------------------------------------------


class LabelOut(BaseModel):
    """Public representation of a label."""

    model_config = ConfigDict(from_attributes=True)

    name: str


class PhotoOut(BaseModel):
    """Public representation of a photo attached to a note."""

    model_config = ConfigDict(from_attributes=True)

    cdn_url: str
    position: int


class PhotoIn(BaseModel):
    """CMS input schema for a photo reference (after S3 upload)."""

    s3_key: str
    cdn_url: str
    position: int = Field(ge=1, le=2)


# ---------------------------------------------------------------------------
# Public response schemas
# ---------------------------------------------------------------------------


class NoteListItem(BaseModel):
    """Compact note representation used in paginated list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    excerpt: str  # first 200 chars of plain-text body
    published_at: datetime
    labels: list[LabelOut]


class NoteDetail(BaseModel):
    """Full note representation returned by the single-note endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body_html: str
    published_at: datetime
    labels: list[LabelOut]
    photos: list[PhotoOut]


class CmsNoteDetail(BaseModel):
    """Full note representation for CMS endpoints (includes drafts with null published_at)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body_html: str
    status: str
    published_at: datetime | None = None
    labels: list[LabelOut]
    photos: list[PhotoOut]


class PaginatedNotes(BaseModel):
    """Wrapper for paginated note list responses."""

    total: int
    page: int
    page_size: int
    items: list[NoteListItem]


# ---------------------------------------------------------------------------
# CMS request schemas
# ---------------------------------------------------------------------------


class NoteCreate(BaseModel):
    """Payload for creating a new note via the CMS."""

    title: str = Field(min_length=1, max_length=100)
    body_html: str = Field(min_length=1, max_length=50_000)
    status: Literal["draft", "published"] = "draft"
    published_at: datetime | None = None
    labels: list[str] = Field(default=[], max_length=20)
    photos: list[PhotoIn] = Field(default=[], max_length=2)


class NoteUpdate(BaseModel):
    """Payload for updating an existing note via the CMS.

    All fields are optional; only supplied fields are applied.
    """

    title: str | None = Field(default=None, min_length=1, max_length=100)
    body_html: str | None = Field(default=None, min_length=1, max_length=50_000)
    status: Literal["draft", "published"] | None = None
    published_at: datetime | None = None
    labels: list[str] | None = Field(default=None, max_length=20)
    photos: list[PhotoIn] | None = Field(default=None, max_length=2)


# ---------------------------------------------------------------------------
# Photo presign schemas
# ---------------------------------------------------------------------------


class PresignRequest(BaseModel):
    """Request body for the photo presign endpoint."""

    filename: str
    content_type: str


class PresignResponse(BaseModel):
    """Response from the photo presign endpoint."""

    upload_url: str
    s3_key: str
    cdn_url: str


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """CMS login request body."""

    password: str


class TokenResponse(BaseModel):
    """JWT token response returned after successful login."""

    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Trip nested schemas
# ---------------------------------------------------------------------------


class TripPhotoIn(BaseModel):
    """CMS input schema for a trip photo reference (after S3 upload)."""

    s3_key: str
    cdn_url: str
    position: int = Field(ge=1, le=20)


class TripPhotoOut(BaseModel):
    """Public representation of a photo attached to a trip."""

    model_config = ConfigDict(from_attributes=True)

    cdn_url: str
    position: int


class CmsTripPhotoOut(BaseModel):
    """CMS representation of a trip photo (includes s3_key for edit forms)."""

    model_config = ConfigDict(from_attributes=True)

    s3_key: str
    cdn_url: str
    position: int


# ---------------------------------------------------------------------------
# Trip public response schemas
# ---------------------------------------------------------------------------


class TripListItem(BaseModel):
    """Compact trip representation used in paginated list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    trip_date: date
    cover_photo_url: str | None = None


class TripDetail(BaseModel):
    """Full trip representation returned by the single-trip public endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    trip_date: date
    description: str | None = None
    photos: list[TripPhotoOut]


class CmsTripDetail(BaseModel):
    """Full trip representation for CMS endpoints (includes drafts)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    trip_date: date
    description: str | None = None
    status: str
    published_at: datetime | None = None
    photos: list[CmsTripPhotoOut]


class PaginatedTrips(BaseModel):
    """Wrapper for paginated trip list responses."""

    total: int
    page: int
    page_size: int
    items: list[TripListItem]


# ---------------------------------------------------------------------------
# Trip CMS request schemas
# ---------------------------------------------------------------------------


class TripCreate(BaseModel):
    """Payload for creating a new trip via the CMS."""

    title: str = Field(min_length=1, max_length=150)
    trip_date: date
    description: str | None = Field(default=None, max_length=2000)
    status: Literal["draft", "published"] = "draft"
    photos: list[TripPhotoIn] = Field(default=[], max_length=20)


class TripUpdate(BaseModel):
    """Payload for updating an existing trip via the CMS.

    All fields are optional; only supplied fields are applied.
    """

    title: str | None = Field(default=None, min_length=1, max_length=150)
    trip_date: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    status: Literal["draft", "published"] | None = None
    photos: list[TripPhotoIn] | None = Field(default=None, max_length=20)


# ---------------------------------------------------------------------------
# Art piece schemas
# ---------------------------------------------------------------------------


class ArtPieceCreate(BaseModel):
    """Payload for creating a new art piece via the CMS."""

    year: int = Field(ge=2020)
    s3_key: str
    cdn_url: str
    title: str | None = Field(default=None, max_length=200)

    @field_validator("year")
    @classmethod
    def year_not_in_future(cls, v: int) -> int:
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(
                f"Year must be between 2020 and {current_year} (inclusive)"
            )
        return v


class ArtPieceUpdate(BaseModel):
    """Payload for updating an existing art piece via the CMS.

    All fields are optional; only supplied fields are applied.
    """

    title: str | None = Field(default=None, max_length=200)
    status: Literal["draft", "published"] | None = None


class ArtPieceBulkReorder(BaseModel):
    """Payload for reordering art pieces within a year."""

    year: int = Field(ge=2020)
    order: list[int] = Field(min_length=1)

    @field_validator("year")
    @classmethod
    def year_not_in_future(cls, v: int) -> int:
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(
                f"Year must be between 2020 and {current_year} (inclusive)"
            )
        return v


class ArtPieceOut(BaseModel):
    """Public representation of an art piece."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cdn_url: str
    title: str | None = None
    position: int


class CmsArtPieceOut(BaseModel):
    """CMS representation of an art piece (includes s3_key, status)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    s3_key: str
    cdn_url: str
    title: str | None = None
    position: int
    status: str


class YearSummary(BaseModel):
    """Year list item for the public year list endpoint."""

    year: int
    cover_photo_url: str | None = None
    count: int


class CmsYearGroup(BaseModel):
    """CMS year group containing all art pieces for a year."""

    year: int
    pieces: list[CmsArtPieceOut]
