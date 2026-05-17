"""Public API endpoints for Family Trips — no authentication required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Trip, TripPhoto
from app.schemas import PaginatedTrips, TripDetail, TripListItem, TripPhotoOut

router = APIRouter(prefix="/api", tags=["public-trips"])


@router.get("/trips", response_model=PaginatedTrips)
def list_trips(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PaginatedTrips:
    """Return a paginated list of published trips, newest first."""

    # Count total published trips
    total = db.scalar(
        select(func.count(Trip.id)).where(Trip.status == "published")
    )

    # Fetch the page of trips with photos eagerly loaded
    offset = (page - 1) * page_size
    trips = (
        db.execute(
            select(Trip)
            .where(Trip.status == "published")
            .order_by(Trip.trip_date.desc(), Trip.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(joinedload(Trip.photos))
        )
        .scalars()
        .unique()
        .all()
    )

    # Build response items
    items = []
    for trip in trips:
        # Cover photo is the photo at position 1
        cover_photo = next(
            (p for p in trip.photos if p.position == 1), None
        )
        items.append(
            TripListItem(
                id=trip.id,
                title=trip.title,
                trip_date=trip.trip_date,
                cover_photo_url=cover_photo.cdn_url if cover_photo else None,
            )
        )

    return PaginatedTrips(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/trips/{trip_id}", response_model=TripDetail)
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
) -> TripDetail:
    """Return the full detail of a single published trip."""

    trip = (
        db.execute(
            select(Trip)
            .where(Trip.id == trip_id, Trip.status == "published")
            .options(joinedload(Trip.photos))
        )
        .scalars()
        .unique()
        .first()
    )

    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Sort photos by position ascending
    sorted_photos = sorted(trip.photos, key=lambda p: p.position)

    return TripDetail(
        id=trip.id,
        title=trip.title,
        trip_date=trip.trip_date,
        description=trip.description,
        photos=[
            TripPhotoOut(cdn_url=p.cdn_url, position=p.position)
            for p in sorted_photos
        ],
    )
