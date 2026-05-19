"""CMS media management router — presign endpoint supporting both photos and videos."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import boto3
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_author
from app.config import settings
from app.schemas import PresignRequest, PresignResponse

router = APIRouter(prefix="/api/cms/media", tags=["cms-media"])

# Allowed content types mapped to (file_extension, s3_prefix)
_ALLOWED_CONTENT_TYPES: dict[str, tuple[str, str]] = {
    "image/jpeg": ("jpg", "photos"),
    "image/png": ("png", "photos"),
    "video/mp4": ("mp4", "videos"),
    "video/webm": ("webm", "videos"),
}


def _get_s3_client():
    """Create a boto3 S3 client using application settings."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


@router.post(
    "/presign",
    response_model=PresignResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a presigned S3 upload URL for photos or videos",
)
def presign_media_upload(
    body: PresignRequest,
    _author: dict = Depends(get_current_author),
) -> PresignResponse:
    """Generate a presigned S3 PUT URL for uploading a photo or video.

    Validates that the content_type is one of the accepted types (image/jpeg,
    image/png, video/mp4, video/webm), generates a unique S3 key under the
    appropriate prefix, and returns the presigned upload URL along with the CDN URL.
    """
    # Validate content type
    if body.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image/jpeg, image/png, video/mp4, and video/webm content types are accepted.",
        )

    # Derive extension and prefix from content type
    ext, prefix = _ALLOWED_CONTENT_TYPES[body.content_type]

    # Generate S3 key: {prefix}/{year}/{uuid4}.{ext}
    year = datetime.now(timezone.utc).year
    unique_id = uuid.uuid4()
    s3_key = f"{prefix}/{year}/{unique_id}.{ext}"

    # Generate presigned URL
    s3_client = _get_s3_client()
    upload_url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.S3_BUCKET,
            "Key": s3_key,
            "ContentType": body.content_type,
        },
        ExpiresIn=900,  # 15 minutes
    )

    # Construct CDN URL
    cdn_url = f"https://{settings.CLOUDFRONT_DOMAIN}/{s3_key}"

    return PresignResponse(
        upload_url=upload_url,
        s3_key=s3_key,
        cdn_url=cdn_url,
    )
