"""Public API endpoints for Emi's Big Moments — no authentication required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Moment, MomentPhoto
from app.schemas import MomentDetail, MomentListItem, MomentPhotoOut, PaginatedMoments

router = APIRouter(prefix="/api", tags=["public-moments"])


@router.get("/moments", response_model=PaginatedMoments)
def list_moments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PaginatedMoments:
    """Return a paginated list of published moments, newest first."""

    # Count total published moments
    total = db.scalar(
        select(func.count(Moment.id)).where(Moment.status == "published")
    )

    # Fetch the page of moments with photos eagerly loaded
    offset = (page - 1) * page_size
    moments = (
        db.execute(
            select(Moment)
            .where(Moment.status == "published")
            .order_by(Moment.moment_date.desc(), Moment.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(joinedload(Moment.photos))
        )
        .scalars()
        .unique()
        .all()
    )

    # Build response items
    items = []
    for moment in moments:
        # Cover photo is the photo at position 1
        cover_photo = next(
            (p for p in moment.photos if p.position == 1), None
        )
        items.append(
            MomentListItem(
                id=moment.id,
                title=moment.title,
                moment_date=moment.moment_date,
                cover_photo_url=cover_photo.cdn_url if cover_photo else None,
            )
        )

    return PaginatedMoments(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/moments/{moment_id}", response_model=MomentDetail)
def get_moment(
    moment_id: int,
    db: Session = Depends(get_db),
) -> MomentDetail:
    """Return the full detail of a single published moment."""

    moment = (
        db.execute(
            select(Moment)
            .where(Moment.id == moment_id, Moment.status == "published")
            .options(joinedload(Moment.photos))
        )
        .scalars()
        .unique()
        .first()
    )

    if moment is None:
        raise HTTPException(status_code=404, detail="Moment not found")

    # Sort photos by position ascending
    sorted_photos = sorted(moment.photos, key=lambda p: p.position)

    return MomentDetail(
        id=moment.id,
        title=moment.title,
        moment_date=moment.moment_date,
        description=moment.description,
        photos=[
            MomentPhotoOut(cdn_url=p.cdn_url, position=p.position)
            for p in sorted_photos
        ],
    )
