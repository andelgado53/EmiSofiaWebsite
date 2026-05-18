"""CMS art management router — CRUD and reorder endpoints for Emi's art pieces."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import boto3
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_author
from app.config import settings
from app.database import get_db
from app.models import ArtPiece
from app.schemas import (
    ArtPieceBulkReorder,
    ArtPieceCreate,
    ArtPieceUpdate,
    CmsArtPieceOut,
    CmsYearGroup,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cms/art", tags=["cms-art"])


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


def _art_piece_to_cms_out(piece: ArtPiece) -> CmsArtPieceOut:
    """Convert an ArtPiece ORM instance to a CmsArtPieceOut response."""
    return CmsArtPieceOut(
        id=piece.id,
        year=piece.year,
        s3_key=piece.s3_key,
        cdn_url=piece.cdn_url,
        title=piece.title,
        position=piece.position,
        status=piece.status,
    )


@router.get(
    "",
    response_model=list[CmsYearGroup],
    summary="List all art pieces grouped by year",
)
def list_art(
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> list[CmsYearGroup]:
    """Return all art pieces grouped by year (newest first), including drafts.

    Requires authentication.
    """
    pieces = db.query(ArtPiece).order_by(ArtPiece.year.desc(), ArtPiece.position.asc()).all()

    # Group by year
    year_groups: dict[int, list[CmsArtPieceOut]] = {}
    for piece in pieces:
        if piece.year not in year_groups:
            year_groups[piece.year] = []
        year_groups[piece.year].append(_art_piece_to_cms_out(piece))

    # Return as list of CmsYearGroup, ordered by year descending
    return [
        CmsYearGroup(year=year, pieces=pieces_list)
        for year, pieces_list in sorted(year_groups.items(), key=lambda x: x[0], reverse=True)
    ]


@router.post(
    "",
    response_model=CmsArtPieceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new art piece",
)
def create_art_piece(
    body: ArtPieceCreate,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsArtPieceOut:
    """Create a new art piece with status 'draft'.

    Assigns the next available position within the specified year
    (max position + 1, or 1 if first piece in that year).
    Requires authentication.
    """
    # Determine next position for this year
    max_position = (
        db.query(func.max(ArtPiece.position))
        .filter(ArtPiece.year == body.year)
        .scalar()
    )
    next_position = (max_position or 0) + 1

    art_piece = ArtPiece(
        year=body.year,
        title=body.title,
        s3_key=body.s3_key,
        cdn_url=body.cdn_url,
        position=next_position,
        status="draft",
    )
    db.add(art_piece)
    db.commit()
    db.refresh(art_piece)

    return _art_piece_to_cms_out(art_piece)


@router.put(
    "/reorder",
    response_model=list[CmsArtPieceOut],
    summary="Reorder art pieces within a year",
)
def reorder_art_pieces(
    body: ArtPieceBulkReorder,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> list[CmsArtPieceOut]:
    """Reorder art pieces within a year.

    Accepts a year and an ordered list of art piece IDs. Assigns positions
    1..N based on array index. Validates all IDs belong to the specified year.
    Requires authentication.
    """
    # Fetch all pieces for the specified year that match the provided IDs
    pieces = (
        db.query(ArtPiece)
        .filter(ArtPiece.year == body.year, ArtPiece.id.in_(body.order))
        .all()
    )

    # Validate all IDs belong to the specified year
    found_ids = {p.id for p in pieces}
    requested_ids = set(body.order)
    if found_ids != requested_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid art piece IDs for the specified year",
        )

    # Create a lookup for quick access
    piece_map = {p.id: p for p in pieces}

    # Assign positions based on array order
    for idx, art_id in enumerate(body.order, start=1):
        piece_map[art_id].position = idx

    db.commit()

    # Return updated pieces in new order
    result = []
    for art_id in body.order:
        db.refresh(piece_map[art_id])
        result.append(_art_piece_to_cms_out(piece_map[art_id]))

    return result


@router.put(
    "/{art_id}",
    response_model=CmsArtPieceOut,
    summary="Update an art piece",
)
def update_art_piece(
    art_id: int,
    body: ArtPieceUpdate,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> CmsArtPieceOut:
    """Update an art piece's title and/or status.

    When status changes to 'published', sets published_at to now.
    Requires authentication.
    """
    art_piece = db.query(ArtPiece).filter(ArtPiece.id == art_id).first()
    if art_piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Art piece not found",
        )

    old_status = art_piece.status

    # Apply fields if provided
    if body.title is not None:
        art_piece.title = body.title

    if body.status is not None:
        art_piece.status = body.status

    # Handle status -> published transition: set published_at if still null
    if (
        old_status != "published"
        and art_piece.status == "published"
        and art_piece.published_at is None
    ):
        art_piece.published_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(art_piece)

    return _art_piece_to_cms_out(art_piece)


@router.delete(
    "/{art_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an art piece",
)
def delete_art_piece(
    art_id: int,
    author: dict = Depends(get_current_author),
    db: Session = Depends(get_db),
) -> None:
    """Delete an art piece by ID.

    Deletes the S3 object (best-effort), removes the DB record, then
    re-sequences positions for remaining pieces in that year to be
    contiguous 1..N.
    Returns 204 No Content on success, 404 if the art piece does not exist.
    Requires authentication.
    """
    art_piece = db.query(ArtPiece).filter(ArtPiece.id == art_id).first()
    if art_piece is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Art piece not found",
        )

    year = art_piece.year
    s3_key = art_piece.s3_key

    # Delete S3 object (best-effort)
    s3_client = _get_s3_client()
    _delete_s3_key(s3_client, s3_key)

    # Delete the art piece from DB
    db.delete(art_piece)
    db.flush()

    # Re-sequence positions for remaining pieces in that year
    remaining_pieces = (
        db.query(ArtPiece)
        .filter(ArtPiece.year == year)
        .order_by(ArtPiece.position.asc())
        .all()
    )
    for idx, piece in enumerate(remaining_pieces, start=1):
        piece.position = idx

    db.commit()
    return None
