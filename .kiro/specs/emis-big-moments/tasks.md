# Implementation Plan: Emi's Big Moments

## Overview

This plan implements the "Emi's Big Moments" feature following the same architectural patterns as Family Trips (FastAPI + SQLAlchemy backend, Next.js frontend, S3/CloudFront photos). The key simplification vs trips: max 2 photos per moment, inline display (no lightbox/gallery), and required descriptions. Work is organized as: database models → backend API → frontend public pages → frontend CMS pages → navigation wiring.

## Tasks

- [x] 1. Set up database models and migration
  - [x] 1.1 Add Moment and MomentPhoto SQLAlchemy models to `backend/app/models.py`
    - Add `Moment` model with fields: id, title (String 150), moment_date (Date), description (Text, NOT NULL), status (String 10, default "draft"), published_at (DateTime, nullable), created_at, updated_at
    - Add `MomentPhoto` model with fields: id, moment_id (FK to moments.id with CASCADE), s3_key (String 512), cdn_url (String 1024), position (Integer), created_at
    - Add relationship from Moment to MomentPhoto with cascade "all, delete-orphan"
    - _Requirements: 2.1, 2.2, 6.4_

  - [x] 1.2 Add Moment Pydantic schemas to `backend/app/schemas.py`
    - Add `MomentPhotoIn` schema (s3_key, cdn_url, position with ge=1 le=2)
    - Add `MomentPhotoOut` schema (cdn_url, position) with `from_attributes=True`
    - Add `CmsMomentPhotoOut` schema (includes s3_key) with `from_attributes=True`
    - Add `MomentCreate` schema (title 1-150 chars, moment_date, description 1-2000 chars, status literal, photos list max 2)
    - Add `MomentUpdate` schema (all fields optional, same constraints)
    - Add `MomentListItem` schema (id, title, moment_date, cover_photo_url nullable)
    - Add `MomentDetail` schema (id, title, moment_date, description, photos list)
    - Add `CmsMomentDetail` schema (id, title, moment_date, description, status, published_at, photos list of CmsMomentPhotoOut)
    - Add `PaginatedMoments` schema (total, page, page_size, items list of MomentListItem)
    - _Requirements: 2.1, 2.4, 2.5, 4.1, 5.1_

  - [x] 1.3 Create Alembic migration for `moments` and `moment_photos` tables
    - Generate migration depending on the latest existing migration
    - Create `moments` table and `moment_photos` table with foreign key and index on moment_id
    - _Requirements: 6.4_

- [x] 2. Implement public moments API endpoints
  - [x] 2.1 Create `backend/app/routers/public_moments.py` with list and detail endpoints
    - Implement `GET /api/moments` with pagination (page, page_size query params)
    - Filter by status="published", order by moment_date DESC then created_at DESC
    - Return `PaginatedMoments` with cover_photo_url from position-1 photo
    - Implement `GET /api/moments/{moment_id}` returning `MomentDetail` with photos ordered by position ASC
    - Return 404 if moment not found or not published (draft)
    - _Requirements: 1.3, 1.4, 1.6, 1.7, 1.8, 1.9_

  - [x] 2.2 Register public moments router in `backend/app/main.py`
    - Import and include the `public_moments` router
    - _Requirements: 6.7_

  - [ ]* 2.3 Write property test for moment list ordering (Property 1)
    - **Property 1: Moment list ordering**
    - Use Hypothesis to generate sets of published moments with arbitrary dates and creation times
    - Assert response items are ordered by moment_date DESC, then created_at DESC
    - **Validates: Requirements 1.3, 1.4**

  - [ ]* 2.4 Write property test for cover photo from position 1 (Property 2)
    - **Property 2: List item contains cover photo from position 1**
    - Use Hypothesis to generate published moments with 0-2 photos at various positions
    - Assert cover_photo_url matches cdn_url of position-1 photo, or is null when no photos exist
    - **Validates: Requirements 1.6, 1.7**

  - [ ]* 2.5 Write property test for detail response completeness (Property 3)
    - **Property 3: Detail response completeness with photo ordering**
    - Use Hypothesis to generate published moments with random valid content and 0-2 photos
    - Assert detail response includes title, moment_date, description, and all photos ordered by position ascending
    - **Validates: Requirements 1.8, 3.2**

- [x] 3. Implement CMS moments API endpoints
  - [x] 3.1 Create `backend/app/routers/cms_moments.py` with CRUD endpoints
    - Implement `POST /api/cms/moments` — create moment with photos, require JWT auth
    - Implement `GET /api/cms/moments` — list all moments (drafts + published) ordered by moment_date DESC
    - Implement `GET /api/cms/moments/{moment_id}` — get single moment (any status)
    - Implement `PUT /api/cms/moments/{moment_id}` — update moment fields and photos; delete removed photos from S3; re-sequence remaining photo positions starting from 1
    - Implement `DELETE /api/cms/moments/{moment_id}` — delete moment, delete all S3 photos (best-effort), return 204
    - Set published_at when status changes to "published"
    - Validate title required and moment_date required and description required when publishing
    - _Requirements: 4.8, 4.9, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12_

  - [x] 3.2 Register CMS moments router in `backend/app/main.py`
    - Import and include the `cms_moments` router
    - _Requirements: 6.7_

  - [ ]* 3.3 Write property test for input validation boundaries (Property 4)
    - **Property 4: Input validation boundaries**
    - Use Hypothesis to generate strings of various lengths for title (boundary at 1 and 150) and description (boundary at 1 and 2000)
    - Assert titles outside [1, 150] rejected, within accepted; descriptions outside [1, 2000] rejected, within accepted; photo lists >2 rejected
    - **Validates: Requirements 2.1, 2.4, 2.5, 4.1, 4.3, 5.3, 5.5**

  - [ ]* 3.4 Write property test for photo position integrity after removal (Property 5)
    - **Property 5: Photo position integrity after removal**
    - Use Hypothesis to generate moments with 1-2 photos, simulate removal of one photo via PUT
    - Assert remaining photos have sequential position values starting from 1 with no gaps
    - **Validates: Requirements 4.8**

  - [ ]* 3.5 Write property test for cascade deletion completeness (Property 6)
    - **Property 6: Cascade deletion completeness**
    - Use Hypothesis to generate moments with 0-2 photos, delete them via DELETE endpoint
    - Assert zero photo records remain for that moment_id and S3 delete was called for each photo's s3_key
    - **Validates: Requirements 5.11**

  - [ ]* 3.6 Write unit tests for CMS moments endpoints
    - Test create moment with valid data returns 201 with default draft status
    - Test publish moment sets published_at timestamp
    - Test 404 for non-existent moment ID
    - Test 401 for unauthenticated CMS requests
    - Test publish without title returns validation error
    - Test publish without date returns validation error
    - Test publish without description returns validation error
    - Test delete moment returns 204 and removes from DB
    - _Requirements: 2.2, 5.2, 5.3, 5.4, 5.5, 5.12_

- [x] 4. Checkpoint - Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement public frontend pages
  - [x] 5.1 Create `/moments` page at `frontend/app/moments/page.tsx`
    - Server-rendered page with ISR (revalidate: 60)
    - Fetch from `GET /api/moments` and render moment list
    - Display each moment as a card with cover photo thumbnail, title, and date
    - Show placeholder image when moment has no photos
    - Show "No moments available yet" message when list is empty
    - _Requirements: 1.1, 1.3, 1.5, 1.6, 1.7, 6.1, 6.5_

  - [x] 5.2 Create `/moments/[id]` page at `frontend/app/moments/[id]/page.tsx`
    - Server-rendered page with ISR (revalidate: 60)
    - Fetch from `GET /api/moments/{id}` and render moment detail
    - Display title, date, description (preserving paragraph breaks via whitespace-pre-line or splitting on newlines)
    - Display photos inline at full content width, maintaining aspect ratio, stacked vertically with consistent spacing
    - No lightbox or modal overlay for photos
    - Call `notFound()` for missing/draft moments (renders 404 page)
    - _Requirements: 1.8, 1.9, 2.3, 3.1, 3.2, 3.3, 3.4, 6.6_

- [x] 6. Implement CMS frontend pages
  - [x] 6.1 Create `/cms/moments` page at `frontend/app/cms/moments/page.tsx`
    - Client-rendered page with JWT auth
    - List all moments in a table with title, status badge, date, and action links
    - Delete button with confirmation dialog
    - Link to create new moment and edit existing moments
    - _Requirements: 5.7, 5.10, 5.12_

  - [x] 6.2 Create `MomentForm` component at `frontend/components/MomentForm.tsx`
    - Form fields: title (max 150 chars), moment_date (date picker), description textarea (max 2000 chars)
    - Photo upload section: accept only JPEG/PNG up to 10 MB, max 2 photos
    - Upload via presigned S3 URLs (reuse existing `/api/cms/photos/presign` endpoint)
    - Drag-and-drop reordering of photos (update position values automatically)
    - Remove photo button
    - Inline validation: title 1-150 chars required, date required, description 1-2000 chars required for publish
    - Display error messages for validation failures (title length, description length, file type, file size, photo count)
    - _Requirements: 2.4, 2.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.9, 5.1_

  - [x] 6.3 Create `/cms/moments/new` page at `frontend/app/cms/moments/new/page.tsx`
    - Client-rendered page with JWT auth
    - Render MomentForm in create mode
    - On submit, POST to `/api/cms/moments` and redirect to moments list
    - _Requirements: 5.1, 5.2_

  - [x] 6.4 Create `/cms/moments/[id]/edit` page at `frontend/app/cms/moments/[id]/edit/page.tsx`
    - Client-rendered page with JWT auth
    - Fetch existing moment data and render MomentForm in edit mode
    - On submit, PUT to `/api/cms/moments/{id}` and redirect to moments list
    - _Requirements: 5.8, 5.9_

  - [ ]* 6.5 Write unit tests for MomentForm component
    - Test title validation shows error for empty and >150 chars
    - Test description validation shows error for empty and >2000 chars
    - Test photo upload rejects non-JPEG/PNG files with error message
    - Test photo upload rejects files over 10 MB with error message
    - Test photo upload rejects third photo with max-2 error message
    - Test drag-and-drop reorder updates position values
    - _Requirements: 2.4, 2.5, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 7. Navigation wiring and homepage integration
  - [x] 7.1 Add "Emi's Big Moments" card to homepage at `frontend/app/page.tsx`
    - Add a clickable card linking to `/moments`
    - Match existing homepage card styling (use pink/rose color theme)
    - _Requirements: 1.1_

  - [x] 7.2 Add "Emi's Big Moments" link to navigation bar in `frontend/app/layout.tsx`
    - Add navigation link to `/moments` in the site nav bar
    - _Requirements: 1.2_

  - [x] 7.3 Add "Moments" link to CMS navigation in `frontend/app/cms/layout.tsx`
    - Add navigation link to `/cms/moments` in the CMS sidebar/nav
    - _Requirements: 5.12_

  - [ ]* 7.4 Write integration tests for full moment lifecycle
    - Test create draft → edit → publish → verify in public list → delete
    - Test moment delete triggers S3 deletion for each photo
    - Test photo removal re-sequences positions correctly
    - _Requirements: 4.8, 5.6, 5.9, 5.11_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The backend uses Python (FastAPI, SQLAlchemy, Hypothesis for PBT)
- The frontend uses TypeScript (Next.js)
- Photo upload reuses the existing `cms_photos` presign endpoint — no new S3 infrastructure needed
- Unlike trips, moments display photos inline (no lightbox/gallery) and are limited to 2 photos max

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["2.1", "3.1"] },
    { "id": 3, "tasks": ["2.2", "3.2"] },
    { "id": 4, "tasks": ["2.3", "2.4", "2.5", "3.3", "3.4", "3.5", "3.6"] },
    { "id": 5, "tasks": ["5.1", "5.2", "6.1", "6.2"] },
    { "id": 6, "tasks": ["6.3", "6.4", "6.5"] },
    { "id": 7, "tasks": ["7.1", "7.2", "7.3"] },
    { "id": 8, "tasks": ["7.4"] }
  ]
}
```
