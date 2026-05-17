"""CMS photo management router — presign and delete endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from urllib.parse import unquote

import boto3
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth import get_current_author
from app.config import settings
from app.schemas import PresignRequest, PresignResponse

router = APIRouter(prefix="/api/cms/photos", tags=["cms-photos"])

# Allowed content types and their file extensions
_ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
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
    summary="Generate a presigned S3 upload URL",
)
def presign_photo_upload(
    body: PresignRequest,
    _author: dict = Depends(get_current_author),
) -> PresignResponse:
    """Generate a presigned S3 PUT URL for uploading a photo.

    Validates that the content_type is image/jpeg or image/png, generates a
    unique S3 key, and returns the presigned upload URL along with the CDN URL.
    """
    # Validate content type
    if body.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image/jpeg and image/png content types are accepted.",
        )

    # Derive extension from content type
    ext = _ALLOWED_CONTENT_TYPES[body.content_type]

    # Generate S3 key: photos/{year}/{uuid4}.{ext}
    year = datetime.now(timezone.utc).year
    unique_id = uuid.uuid4()
    s3_key = f"photos/{year}/{unique_id}.{ext}"

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


@router.delete(
    "/{key:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a photo from S3",
)
def delete_photo(
    key: str,
    author: dict = Depends(get_current_author),
) -> Response:
    """Delete a photo object from S3.

    URL-decodes the key path parameter and calls ``delete_object`` on the
    configured S3 bucket. Returns 204 No Content on success.
    Requires authentication.
    """
    decoded_key = unquote(key)
    client = _get_s3_client()
    client.delete_object(Bucket=settings.S3_BUCKET, Key=decoded_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
