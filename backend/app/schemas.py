"""Pydantic v2 schemas for the Notes for Emi API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
