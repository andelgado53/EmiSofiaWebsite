"""Public API endpoints for Emi's Art — no authentication required."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ArtPiece
from app.schemas import ArtPieceOut, YearSummary

router = APIRouter(prefix="/api/art", tags=["public-art"])


@router.get("/years", response_model=list[YearSummary])
def list_years(
    db: Session = Depends(get_db),
) -> list[YearSummary]:
    """Return years with at least one published art piece, newest first.

    The cover_photo_url for each year is the cdn_url of the published piece
    with the lowest position value in that year.
    """

    # Subquery: for each year, find the minimum position among published pieces
    min_pos_subq = (
        select(
            ArtPiece.year,
            func.min(ArtPiece.position).label("min_position"),
        )
        .where(ArtPiece.status == "published")
        .group_by(ArtPiece.year)
        .subquery()
    )

    # Join back to get the cdn_url of the piece at that min position
    cover_query = (
        select(
            ArtPiece.year,
            ArtPiece.cdn_url,
        )
        .join(
            min_pos_subq,
            (ArtPiece.year == min_pos_subq.c.year)
            & (ArtPiece.position == min_pos_subq.c.min_position),
        )
        .where(ArtPiece.status == "published")
    )

    cover_map: dict[int, str] = {}
    for row in db.execute(cover_query).all():
        cover_map[row.year] = row.cdn_url

    # Count published pieces per year
    count_query = (
        select(
            ArtPiece.year,
            func.count(ArtPiece.id).label("count"),
        )
        .where(ArtPiece.status == "published")
        .group_by(ArtPiece.year)
        .order_by(ArtPiece.year.desc())
    )

    results = []
    for row in db.execute(count_query).all():
        results.append(
            YearSummary(
                year=row.year,
                cover_photo_url=cover_map.get(row.year),
                count=row.count,
            )
        )

    return results


@router.get("/years/{year}", response_model=list[ArtPieceOut])
def get_year_gallery(
    year: int,
    db: Session = Depends(get_db),
) -> list[ArtPieceOut]:
    """Return all published art pieces for a given year, ordered by position ASC.

    Returns an empty array if no published pieces exist for the year.
    """

    pieces = (
        db.execute(
            select(ArtPiece)
            .where(ArtPiece.year == year, ArtPiece.status == "published")
            .order_by(ArtPiece.position.asc())
        )
        .scalars()
        .all()
    )

    return [
        ArtPieceOut(
            id=p.id,
            cdn_url=p.cdn_url,
            title=p.title,
            position=p.position,
            media_type=p.media_type,
        )
        for p in pieces
    ]
