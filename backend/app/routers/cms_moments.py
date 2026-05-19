"""CMS moment management router — CRUD endpoints for Emi's Big Moments."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import boto3
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_author
from app.config import settings
from app.database import get_db
from app.models import Moment, MomentPhoto
from app.schemas import CmsMomentDetail, CmsMomentPhotoOut, MomentCreate, MomentUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cms/moments", tags=["cms-moments"])


def _get_s3_client():
    """Create a boto3 S3 client using application settings."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


def _delete_s3_key(s3_client, key: str) -> None:
    """Delete a single S3 object, logging errors but not raising (best-effort)."""
    try:
        s3_client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
    except Exception:
        logger.exception("Failed to delete S3 object: %s", key)


def _moment_to_cms_detail(moment: Moment) -> CmsMomentDetail:
    """Convert a Moment ORM instance to a CmsMomentDetail response."""
    photos_out = sorted(
        [CmsMomentPhotoOut(s3_key=p.s3_key, cdn_url=p.cdn_url, position=p.position, media_type=p.media_type) for p in moment.photos],
        key=lambda p: p.position,
    )
    return CmsMomentDetail(
        id=moment.id,
        title=moment.title,
        moment_date=moment.moment_date,
        description=moment.description,
        status=moment.status,
        published_at=moment.published_at,
        photos=photos_out,
    )


@router.post(
    "",
    response_model=CmsMomentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new moment",
)
def create_moment(
    body: MomentCreate,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsMomentDetail:
    """Create a new moment with photos.

    - Sets ``published_at`` to now if status is ``published``.
    - Validates title, moment_date, and description required when publishing
      (handled by Pydantic schema — title has min_length=1, moment_date is required,
      description has min_length=1).
    - Creates MomentPhoto records from the photos list.
    """
    # Determine published_at
    published_at = None
    if body.status == "published":
        published_at = datetime.now(timezone.utc)

    # Create the Moment record
    moment = Moment(
        title=body.title,
        moment_date=body.moment_date,
        description=body.description,
        status=body.status,
        published_at=published_at,
    )
    db.add(moment)
    db.flush()  # Get the moment.id assigned

    # Create MomentPhoto records
    for photo_in in body.photos:
        photo = MomentPhoto(
            moment_id=moment.id,
            s3_key=photo_in.s3_key,
            cdn_url=photo_in.cdn_url,
            position=photo_in.position,
            media_type=photo_in.media_type,
        )
        db.add(photo)

    db.commit()
    db.refresh(moment)

    return _moment_to_cms_detail(moment)


@router.get(
    "",
    response_model=list[CmsMomentDetail],
    summary="List all moments (drafts and published)",
)
def list_moments(
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> list[CmsMomentDetail]:
    """Return all moments ordered by moment_date descending.

    Includes both draft and published moments. Requires authentication.
    """
    moments = db.query(Moment).order_by(Moment.moment_date.desc()).all()
    return [_moment_to_cms_detail(moment) for moment in moments]


@router.get(
    "/{moment_id}",
    response_model=CmsMomentDetail,
    summary="Get a single moment by ID",
)
def get_moment(
    moment_id: int,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsMomentDetail:
    """Return a single moment regardless of status (draft or published).

    Requires authentication. Returns 404 if the moment does not exist.
    """
    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if moment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moment not found",
        )
    return _moment_to_cms_detail(moment)


@router.put(
    "/{moment_id}",
    response_model=CmsMomentDetail,
    summary="Update an existing moment",
)
def update_moment(
    moment_id: int,
    body: MomentUpdate,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsMomentDetail:
    """Update an existing moment.

    - Only supplied fields are applied (partial update semantics on scalar fields).
    - When ``photos`` are provided, they fully replace the existing ones.
    - Compares old vs new photo lists and deletes removed S3 objects (best-effort).
    - Re-sequences remaining photo positions starting from 1.
    - If transitioning to ``published`` and ``published_at`` is null,
      sets ``published_at = now()``.
    - Returns 404 if the moment does not exist.
    """
    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if moment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moment not found",
        )

    # Track the old status for transition detection
    old_status = moment.status

    # Apply scalar fields if provided
    if body.title is not None:
        moment.title = body.title

    if body.moment_date is not None:
        moment.moment_date = body.moment_date

    if body.description is not None:
        moment.description = body.description

    if body.status is not None:
        moment.status = body.status

    # Handle status -> published transition: set published_at if still null
    if (
        old_status != "published"
        and moment.status == "published"
        and moment.published_at is None
    ):
        moment.published_at = datetime.now(timezone.utc)

    # Replace photos if provided (full replacement)
    if body.photos is not None:
        # Determine which S3 keys were removed
        old_keys = {p.s3_key for p in moment.photos}
        new_keys = {p.s3_key for p in body.photos}
        removed_keys = old_keys - new_keys

        # Delete removed photos from S3 (best-effort)
        if removed_keys:
            s3_client = _get_s3_client()
            for key in removed_keys:
                _delete_s3_key(s3_client, key)

        # Delete existing photo records from DB
        db.query(MomentPhoto).filter(MomentPhoto.moment_id == moment.id).delete()
        db.flush()

        # Create new photo records with re-sequenced positions starting from 1
        for idx, photo_in in enumerate(body.photos, start=1):
            photo = MomentPhoto(
                moment_id=moment.id,
                s3_key=photo_in.s3_key,
                cdn_url=photo_in.cdn_url,
                position=idx,
                media_type=photo_in.media_type,
            )
            db.add(photo)

    db.commit()
    db.refresh(moment)

    return _moment_to_cms_detail(moment)


@router.delete(
    "/{moment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a moment",
)
def delete_moment(
    moment_id: int,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> None:
    """Delete a moment by ID.

    Deletes all associated S3 photo objects (best-effort), then removes
    the moment and its photo records from the database.
    Returns 204 No Content on success, 404 if the moment does not exist.
    Requires authentication.
    """
    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if moment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moment not found",
        )

    # Delete all S3 photos (best-effort)
    if moment.photos:
        s3_client = _get_s3_client()
        for photo in moment.photos:
            _delete_s3_key(s3_client, photo.s3_key)

    # Delete the moment (cascade deletes MomentPhoto rows)
    db.delete(moment)
    db.commit()
    return None
