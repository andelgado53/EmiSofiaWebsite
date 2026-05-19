"""CMS trip management router — CRUD endpoints for family trips."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import boto3
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_author
from app.config import settings
from app.database import get_db
from app.models import Trip, TripPhoto
from app.schemas import CmsTripDetail, CmsTripPhotoOut, TripCreate, TripUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cms/trips", tags=["cms-trips"])


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


def _trip_to_cms_detail(trip: Trip) -> CmsTripDetail:
    """Convert a Trip ORM instance to a CmsTripDetail response."""
    photos_out = sorted(
        [CmsTripPhotoOut(s3_key=p.s3_key, cdn_url=p.cdn_url, position=p.position, media_type=p.media_type) for p in trip.photos],
        key=lambda p: p.position,
    )
    return CmsTripDetail(
        id=trip.id,
        title=trip.title,
        trip_date=trip.trip_date,
        description=trip.description,
        status=trip.status,
        published_at=trip.published_at,
        photos=photos_out,
    )


@router.post(
    "",
    response_model=CmsTripDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trip",
)
def create_trip(
    body: TripCreate,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsTripDetail:
    """Create a new trip with photos.

    - Sets ``published_at`` to now if status is ``published``.
    - Validates title required and trip_date required when publishing
      (handled by Pydantic schema — title has min_length=1, trip_date is required).
    - Creates TripPhoto records from the photos list.
    """
    # Determine published_at
    published_at = None
    if body.status == "published":
        published_at = datetime.now(timezone.utc)

    # Create the Trip record
    trip = Trip(
        title=body.title,
        trip_date=body.trip_date,
        description=body.description,
        status=body.status,
        published_at=published_at,
    )
    db.add(trip)
    db.flush()  # Get the trip.id assigned

    # Create TripPhoto records
    for photo_in in body.photos:
        photo = TripPhoto(
            trip_id=trip.id,
            s3_key=photo_in.s3_key,
            cdn_url=photo_in.cdn_url,
            position=photo_in.position,
            media_type=photo_in.media_type,
        )
        db.add(photo)

    db.commit()
    db.refresh(trip)

    return _trip_to_cms_detail(trip)


@router.get(
    "",
    response_model=list[CmsTripDetail],
    summary="List all trips (drafts and published)",
)
def list_trips(
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> list[CmsTripDetail]:
    """Return all trips ordered by created_at descending.

    Includes both draft and published trips. Requires authentication.
    """
    trips = db.query(Trip).order_by(Trip.created_at.desc()).all()
    return [_trip_to_cms_detail(trip) for trip in trips]


@router.get(
    "/{trip_id}",
    response_model=CmsTripDetail,
    summary="Get a single trip by ID",
)
def get_trip(
    trip_id: int,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsTripDetail:
    """Return a single trip regardless of status (draft or published).

    Requires authentication. Returns 404 if the trip does not exist.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    return _trip_to_cms_detail(trip)


@router.put(
    "/{trip_id}",
    response_model=CmsTripDetail,
    summary="Update an existing trip",
)
def update_trip(
    trip_id: int,
    body: TripUpdate,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsTripDetail:
    """Update an existing trip.

    - Only supplied fields are applied (partial update semantics on scalar fields).
    - When ``photos`` are provided, they fully replace the existing ones.
    - Compares old vs new photo lists and deletes removed S3 objects (best-effort).
    - If transitioning to ``published`` and ``published_at`` is null,
      sets ``published_at = now()``.
    - Returns 404 if the trip does not exist.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # Track the old status for transition detection
    old_status = trip.status

    # Apply scalar fields if provided
    if body.title is not None:
        trip.title = body.title

    if body.trip_date is not None:
        trip.trip_date = body.trip_date

    if body.description is not None:
        trip.description = body.description

    if body.status is not None:
        trip.status = body.status

    # Handle status -> published transition: set published_at if still null
    if (
        old_status != "published"
        and trip.status == "published"
        and trip.published_at is None
    ):
        trip.published_at = datetime.now(timezone.utc)

    # Replace photos if provided (full replacement)
    if body.photos is not None:
        # Determine which S3 keys were removed
        old_keys = {p.s3_key for p in trip.photos}
        new_keys = {p.s3_key for p in body.photos}
        removed_keys = old_keys - new_keys

        # Delete removed photos from S3 (best-effort)
        if removed_keys:
            s3_client = _get_s3_client()
            for key in removed_keys:
                _delete_s3_key(s3_client, key)

        # Delete existing photo records from DB
        db.query(TripPhoto).filter(TripPhoto.trip_id == trip.id).delete()
        db.flush()

        # Create new photo records
        for photo_in in body.photos:
            photo = TripPhoto(
                trip_id=trip.id,
                s3_key=photo_in.s3_key,
                cdn_url=photo_in.cdn_url,
                position=photo_in.position,
                media_type=photo_in.media_type,
            )
            db.add(photo)

    db.commit()
    db.refresh(trip)

    return _trip_to_cms_detail(trip)


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a trip",
)
def delete_trip(
    trip_id: int,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> None:
    """Delete a trip by ID.

    Deletes all associated S3 photo objects (best-effort), then removes
    the trip and its photo records from the database.
    Returns 204 No Content on success, 404 if the trip does not exist.
    Requires authentication.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    # Delete all S3 photos (best-effort)
    if trip.photos:
        s3_client = _get_s3_client()
        for photo in trip.photos:
            _delete_s3_key(s3_client, photo.s3_key)

    # Delete the trip (cascade deletes TripPhoto rows)
    db.delete(trip)
    db.commit()
    return None
