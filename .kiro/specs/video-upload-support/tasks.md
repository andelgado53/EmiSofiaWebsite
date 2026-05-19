# Implementation Plan: Video Upload Support

## Overview

This plan extends the existing media infrastructure to support video uploads (MP4 and WebM) alongside photos across Art, Moments, and Trips. The implementation adds a `media_type` discriminator column to existing photo tables, creates a new media presign endpoint, updates CMS and public API routers, and extends frontend components for video upload and playback.

## Tasks

- [x] 1. Database migration and model updates
  - [x] 1.1 Create Alembic migration to add media_type column
    - Create a new Alembic migration file that adds a `media_type` column of type `String(10)` with `NOT NULL` constraint and `server_default="photo"` to `moment_photos`, `trip_photos`, and `art_pieces` tables
    - Include a `downgrade()` function that drops the `media_type` column from all three tables
    - Ensure the migration declares the correct `down_revision` linking to the previous migration (`d8a4e2b19c73`)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [x] 1.2 Update SQLAlchemy models with media_type field
    - Add `media_type: Mapped[str] = mapped_column(String(10), nullable=False, server_default="photo")` to `MomentPhoto`, `TripPhoto`, and `ArtPiece` models in `backend/app/models.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 2. Backend schema and presign endpoint
  - [x] 2.1 Update Pydantic schemas with media_type field
    - Add `media_type: Literal["photo", "video"] = "photo"` to `MomentPhotoIn`, `TripPhotoIn`, and `ArtPieceCreate` schemas
    - Add `media_type: str` to `MomentPhotoOut`, `TripPhotoOut`, `ArtPieceOut`, `CmsMomentPhotoOut`, `CmsTripPhotoOut`, and `CmsArtPieceOut` schemas
    - _Requirements: 3.6, 4.3, 5.3, 6.2_

  - [x] 2.2 Create media presign endpoint
    - Create `backend/app/routers/cms_media.py` with a `POST /api/cms/media/presign` endpoint
    - Define `_ALLOWED_CONTENT_TYPES` mapping: `image/jpeg` → `("jpg", "photos")`, `image/png` → `("png", "photos")`, `video/mp4` → `("mp4", "videos")`, `video/webm` → `("webm", "videos")`
    - Validate `content_type` against allowed types, return HTTP 400 with descriptive error for invalid types
    - Generate S3 key as `{prefix}/{year}/{uuid4}.{ext}` and CDN URL as `https://{CLOUDFRONT_DOMAIN}/{s3_key}`
    - Generate presigned PUT URL with 900-second expiry
    - Require authentication via `get_current_author` dependency
    - Register the new router in `backend/app/main.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 2.3 Write property test for presign key generation (Property 1)
    - **Property 1: Presign key generation correctness**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [ ]* 2.4 Write property test for invalid content type rejection (Property 2)
    - **Property 2: Invalid content type rejection**
    - **Validates: Requirements 1.4**

- [x] 3. Checkpoint - Ensure migration and presign endpoint work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Update CMS routers for video support
  - [x] 4.1 Update CMS Moments router to handle media_type
    - Update `create_moment` to pass `media_type` from `MomentPhotoIn` to `MomentPhoto` record creation
    - Update `update_moment` to pass `media_type` when replacing photo records
    - Update `_moment_to_cms_detail` to include `media_type` in `CmsMomentPhotoOut`
    - _Requirements: 4.1, 4.2, 4.4, 4.5_

  - [x] 4.2 Update CMS Trips router to handle media_type
    - Update `create_trip` to pass `media_type` from `TripPhotoIn` to `TripPhoto` record creation
    - Update `update_trip` to pass `media_type` when replacing photo records
    - Update `_trip_to_cms_detail` to include `media_type` in `CmsTripPhotoOut`
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.6_

  - [x] 4.3 Update CMS Art router to handle media_type
    - Update `create_art_piece` to pass `media_type` from `ArtPieceCreate` to `ArtPiece` record creation
    - Update `_art_piece_to_cms_out` to include `media_type` in `CmsArtPieceOut`
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 4.4 Write property test for media_type default value (Property 4)
    - **Property 4: media_type default value**
    - **Validates: Requirements 3.4**

  - [ ]* 4.5 Write property test for invalid media_type rejection (Property 5)
    - **Property 5: Invalid media_type rejection**
    - **Validates: Requirements 3.6, 4.3, 5.3, 6.2**

  - [ ]* 4.6 Write property test for media_type round-trip preservation (Property 6)
    - **Property 6: media_type round-trip preservation**
    - **Validates: Requirements 4.1, 4.2, 5.1, 5.2, 6.1, 6.3**

- [x] 5. Update public API routers
  - [x] 5.1 Update public Moments API to include media_type
    - Update `get_moment` endpoint to include `media_type` in `MomentPhotoOut` response
    - _Requirements: 8.3_

  - [x] 5.2 Update public Trips API to include media_type
    - Update `get_trip` endpoint to include `media_type` in `TripPhotoOut` response
    - _Requirements: 9.3_

  - [x] 5.3 Update public Art API to include media_type
    - Update `get_year_gallery` endpoint to include `media_type` in `ArtPieceOut` response
    - _Requirements: 10.3_

  - [ ]* 5.4 Write property test for public API media_type inclusion (Property 8)
    - **Property 8: Public API media_type inclusion**
    - **Validates: Requirements 8.3, 9.3, 10.3**

- [x] 6. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Frontend upload component video support
  - [x] 7.1 Install fast-check dev dependency
    - Add `fast-check` as a dev dependency in `frontend/package.json`
    - _Requirements: (testing infrastructure)_

  - [x] 7.2 Create MediaUpload component with video support
    - Create `frontend/components/MediaUpload.tsx` extending the existing `PhotoUpload` pattern
    - Define `ALLOWED_TYPES` map with content types and max sizes: images 10 MB, videos 100 MB
    - Define `EXT_TO_CONTENT_TYPE` fallback map for empty MIME types (`.mp4` → `video/mp4`, `.webm` → `video/webm`, `.jpg`/`.jpeg` → `image/jpeg`, `.png` → `image/png`)
    - Validate file type by MIME or extension fallback, reject 0-byte files
    - Apply size limit based on media type (10 MB photos, 100 MB videos)
    - Call the new `/api/cms/media/presign` endpoint with the resolved `content_type`
    - Include `media_type: "photo" | "video"` in the returned `MediaData` based on content type
    - Show video icon overlay on video thumbnails; use static placeholder for video preview
    - Display appropriate error messages for invalid file type, oversized files, and empty files
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 2.1, 2.2, 2.3, 2.4_

  - [ ]* 7.3 Write property test for file size validation (Property 3)
    - **Property 3: File size validation by media type**
    - **Validates: Requirements 2.1, 2.2, 2.4**

  - [ ]* 7.4 Write property test for extension-to-MIME fallback (Property 7)
    - **Property 7: File extension to MIME type fallback**
    - **Validates: Requirements 7.3**

- [x] 8. Frontend video playback and page updates
  - [x] 8.1 Create VideoPlayer component
    - Create `frontend/components/VideoPlayer.tsx` with native HTML5 `<video>` element
    - Include `controls` attribute, no `autoplay`
    - Show static fallback message on error event ("Video unavailable")
    - Ensure keyboard accessibility via native controls (focusable)
    - Accept `src`, `alt`, and `className` props
    - _Requirements: 8.1, 8.2, 8.4, 9.1, 9.2, 9.4, 10.1, 10.2, 10.4, 10.5_

  - [x] 8.2 Update Moments detail page for video playback
    - Update the Moments detail page to conditionally render `<VideoPlayer>` for items with `media_type === "video"` and `<img>` for photos
    - _Requirements: 8.1, 8.2, 8.4_

  - [x] 8.3 Update Trips detail page for video playback
    - Update the Trips detail page / PhotoGallery component to conditionally render `<VideoPlayer>` for items with `media_type === "video"` and `<img>` for photos
    - _Requirements: 9.1, 9.2, 9.4_

  - [x] 8.4 Update Art gallery page for video playback
    - Update the Art gallery page to render `<VideoPlayer>` for art pieces with `media_type === "video"` instead of `<img>`
    - _Requirements: 10.1, 10.2, 10.4, 10.5_

  - [x] 8.5 Update CMS forms to use MediaUpload component
    - Update `MomentForm.tsx` to use the new `MediaUpload` component instead of `PhotoUploader`
    - Update `TripForm.tsx` to use the new `MediaUpload` component instead of `PhotoUploader`
    - Update the CMS Art upload flow to use the new media presign endpoint and pass `media_type`
    - _Requirements: 4.1, 4.2, 5.1, 5.2, 6.1_

  - [ ]* 8.6 Write unit tests for VideoPlayer component
    - Test that `<video>` renders with `controls` attribute and without `autoplay`
    - Test that error event triggers fallback message display
    - Test keyboard accessibility (element is focusable)
    - _Requirements: 8.2, 8.4, 10.2, 10.4, 10.5_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The existing `/api/cms/photos/presign` endpoint remains unchanged for backward compatibility
- S3 deletion logic works unchanged for both photos and videos (same `_delete_s3_key` function)
- The backend uses Python (FastAPI + SQLAlchemy + Hypothesis for PBT)
- The frontend uses TypeScript (Next.js + Vitest + fast-check for PBT)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3", "2.4", "4.1", "4.2", "4.3"] },
    { "id": 3, "tasks": ["4.4", "4.5", "4.6", "5.1", "5.2", "5.3"] },
    { "id": 4, "tasks": ["5.4", "7.1"] },
    { "id": 5, "tasks": ["7.2", "8.1"] },
    { "id": 6, "tasks": ["7.3", "7.4", "8.2", "8.3", "8.4", "8.5"] },
    { "id": 7, "tasks": ["8.6"] }
  ]
}
```
