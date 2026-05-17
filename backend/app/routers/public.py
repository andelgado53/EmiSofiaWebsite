"""Public API endpoints — no authentication required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Note, NoteLabel
from app.schemas import NoteDetail, NoteListItem, PaginatedNotes
from app.utils import generate_excerpt

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/notes", response_model=PaginatedNotes)
def list_notes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PaginatedNotes:
    """Return a paginated list of published notes, newest first."""

    # Count total published notes
    total = db.scalar(
        select(func.count(Note.id)).where(Note.status == "published")
    )

    # Fetch the page of notes with labels eagerly loaded
    offset = (page - 1) * page_size
    notes = (
        db.execute(
            select(Note)
            .where(Note.status == "published")
            .order_by(Note.published_at.desc(), Note.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(joinedload(Note.note_labels).joinedload(NoteLabel.label))
        )
        .scalars()
        .unique()
        .all()
    )

    # Build response items
    items = [
        NoteListItem(
            id=note.id,
            title=note.title,
            excerpt=generate_excerpt(note.body_html),
            published_at=note.published_at,
            labels=[{"name": label.name} for label in note.labels],
        )
        for note in notes
    ]

    return PaginatedNotes(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/notes/{note_id}", response_model=NoteDetail)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
) -> NoteDetail:
    """Return the full detail of a single published note."""

    note = (
        db.execute(
            select(Note)
            .where(Note.id == note_id, Note.status == "published")
            .options(
                joinedload(Note.note_labels).joinedload(NoteLabel.label),
                joinedload(Note.photos),
            )
        )
        .scalars()
        .unique()
        .first()
    )

    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    # Sort photos by position ascending
    sorted_photos = sorted(note.photos, key=lambda p: p.position)

    return NoteDetail(
        id=note.id,
        title=note.title,
        body_html=note.body_html,
        published_at=note.published_at,
        labels=[{"name": label.name} for label in note.labels],
        photos=[{"cdn_url": p.cdn_url, "position": p.position} for p in sorted_photos],
    )
