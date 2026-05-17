"""CMS note management router — CRUD endpoints for notes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_author
from app.database import get_db
from app.models import Label, Note, NoteLabel, Photo
from app.schemas import NoteCreate, NoteUpdate, CmsNoteDetail, LabelOut, PhotoOut
from app.utils import normalise_labels, sanitise_html

router = APIRouter(prefix="/api/cms/notes", tags=["cms-notes"])


@router.post(
    "",
    response_model=CmsNoteDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new note",
)
def create_note(
    body: NoteCreate,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsNoteDetail:
    """Create a new note with labels and photos.

    - Sanitises ``body_html`` before persisting.
    - Normalises and upserts labels.
    - Sets ``published_at`` to now if status is ``published`` and no
      ``published_at`` was provided.
    - Creates Photo records from the photos list.
    - Returns the created note as a NoteDetail schema.
    """
    # Sanitise HTML body
    clean_html = sanitise_html(body.body_html)

    # Determine published_at
    published_at = body.published_at
    if body.status == "published" and published_at is None:
        published_at = datetime.now(timezone.utc)

    # Create the Note record
    note = Note(
        title=body.title,
        body_html=clean_html,
        status=body.status,
        published_at=published_at,
    )
    db.add(note)
    db.flush()  # Get the note.id assigned

    # Normalise and upsert labels
    normalised = normalise_labels(body.labels)
    for label_name in normalised:
        # Try to find existing label
        label = db.query(Label).filter(Label.name == label_name).first()
        if label is None:
            label = Label(name=label_name)
            db.add(label)
            db.flush()  # Get the label.id assigned

        # Create the association
        note_label = NoteLabel(note_id=note.id, label_id=label.id)
        db.add(note_label)

    # Create Photo records
    for photo_in in body.photos:
        photo = Photo(
            note_id=note.id,
            s3_key=photo_in.s3_key,
            cdn_url=photo_in.cdn_url,
            position=photo_in.position,
        )
        db.add(photo)

    db.commit()
    db.refresh(note)

    # Build the response
    labels_out = [LabelOut(name=lbl.name) for lbl in note.labels]
    photos_out = sorted(
        [PhotoOut(cdn_url=p.cdn_url, position=p.position) for p in note.photos],
        key=lambda p: p.position,
    )

    return CmsNoteDetail(
        id=note.id,
        title=note.title,
        body_html=note.body_html,
        status=note.status,
        published_at=note.published_at,
        labels=labels_out,
        photos=photos_out,
    )


def _note_to_cms_detail(note: Note) -> CmsNoteDetail:
    """Convert a Note ORM instance to a CmsNoteDetail response."""
    labels_out = [LabelOut(name=lbl.name) for lbl in note.labels]
    photos_out = sorted(
        [PhotoOut(cdn_url=p.cdn_url, position=p.position) for p in note.photos],
        key=lambda p: p.position,
    )
    return CmsNoteDetail(
        id=note.id,
        title=note.title,
        body_html=note.body_html,
        status=note.status,
        published_at=note.published_at,
        labels=labels_out,
        photos=photos_out,
    )


@router.get(
    "",
    response_model=list[CmsNoteDetail],
    summary="List all notes (drafts and published)",
)
def list_notes(
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> list[CmsNoteDetail]:
    """Return all notes ordered by created_at descending.

    Includes both draft and published notes. Requires authentication.
    """
    notes = db.query(Note).order_by(Note.created_at.desc()).all()
    return [_note_to_cms_detail(note) for note in notes]


@router.get(
    "/{note_id}",
    response_model=CmsNoteDetail,
    summary="Get a single note by ID",
)
def get_note(
    note_id: int,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsNoteDetail:
    """Return a single note regardless of status (draft or published).

    Requires authentication. Returns 404 if the note does not exist.
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    return _note_to_cms_detail(note)


@router.put(
    "/{note_id}",
    response_model=CmsNoteDetail,
    summary="Update an existing note",
)
def update_note(
    note_id: int,
    body: NoteUpdate,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsNoteDetail:
    """Update an existing note.

    - Only supplied fields are applied (partial update semantics on scalar fields).
    - When ``labels`` or ``photos`` are provided, they fully replace the existing ones.
    - Sanitises ``body_html`` before persisting (if provided).
    - If transitioning from ``draft`` to ``published`` and ``published_at`` is null,
      sets ``published_at = now()``.
    - Returns 404 if the note does not exist.
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )

    # Track the old status for transition detection
    old_status = note.status

    # Apply scalar fields if provided
    if body.title is not None:
        note.title = body.title

    if body.body_html is not None:
        note.body_html = sanitise_html(body.body_html)

    if body.status is not None:
        note.status = body.status

    if body.published_at is not None:
        note.published_at = body.published_at

    # Handle draft -> published transition: set published_at if still null
    if (
        old_status == "draft"
        and note.status == "published"
        and note.published_at is None
    ):
        note.published_at = datetime.now(timezone.utc)

    # Replace labels if provided (full replacement)
    if body.labels is not None:
        # Delete existing label associations
        db.query(NoteLabel).filter(NoteLabel.note_id == note.id).delete()
        db.flush()

        # Normalise and upsert new labels
        normalised = normalise_labels(body.labels)
        for label_name in normalised:
            label = db.query(Label).filter(Label.name == label_name).first()
            if label is None:
                label = Label(name=label_name)
                db.add(label)
                db.flush()

            note_label = NoteLabel(note_id=note.id, label_id=label.id)
            db.add(note_label)

    # Replace photos if provided (full replacement)
    if body.photos is not None:
        # Delete existing photos
        db.query(Photo).filter(Photo.note_id == note.id).delete()
        db.flush()

        # Create new photo records
        for photo_in in body.photos:
            photo = Photo(
                note_id=note.id,
                s3_key=photo_in.s3_key,
                cdn_url=photo_in.cdn_url,
                position=photo_in.position,
            )
            db.add(photo)

    db.commit()
    db.refresh(note)

    # Build the response
    labels_out = [LabelOut(name=lbl.name) for lbl in note.labels]
    photos_out = sorted(
        [PhotoOut(cdn_url=p.cdn_url, position=p.position) for p in note.photos],
        key=lambda p: p.position,
    )

    return CmsNoteDetail(
        id=note.id,
        title=note.title,
        body_html=note.body_html,
        status=note.status,
        published_at=note.published_at,
        labels=labels_out,
        photos=photos_out,
    )


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
)
def delete_note(
    note_id: int,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> None:
    """Delete a note by ID.

    Cascade deletes associated NoteLabel and Photo rows automatically
    (ON DELETE CASCADE). Returns 204 No Content on success, 404 if the
    note does not exist. Requires authentication.
    """
    note = db.query(Note).filter(Note.id == note_id).first()
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    db.delete(note)
    db.commit()
    return None
