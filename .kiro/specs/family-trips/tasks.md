# Implementation Plan: Family Trips

## Overview

This plan implements the Family Trips feature following the existing architectural patterns (FastAPI + SQLAlchemy backend, Next.js frontend). Work is organized as: database models → backend API → frontend public pages → frontend CMS pages → integration wiring. Each step builds incrementally on the previous one.

## Tasks

- [x] 1. Set up database models and migration
  - [x] 1.1 Add Trip and TripPhoto SQLAlchemy models to `backend/app/models.py`
    - Add `Trip` model with fields: id, title (String 150), trip_date (Date), description (Text, nullable), status (String 10, default "draft"), published_at (DateTime, nullable), created_at, updated_at
    - Add `TripPhoto` model with fields: id, trip_id (FK to trips.id with CASCADE), s3_key (String 512), cdn_url (String 1024), position (Integer), created_at
    - Add relationship from Trip to TripPhoto with cascade "all, delete-orphan"
    - _Requirements: 2.1, 2.2, 7.4_

  - [x] 1.2 Add Trip Pydantic schemas to `backend/app/schemas.py`
    - Add `TripPhotoIn` schema (s3_key, cdn_url, position with ge=1 le=20)
    - Add `TripPhotoOut` schema (cdn_url, position) with `from_attributes=True`
    - Add `TripCreate` schema (title 1-150 chars, trip_date, description max 2000, status literal, photos list max 20)
    - Add `TripUpdate` schema (all fields optional, same constraints)
    - Add `TripListItem` schema (id, title, trip_date, cover_photo_url nullable)
    - Add `TripDetail` schema (id, title, trip_date, description, photos list)
    - Add `CmsTripDetail` schema (id, title, trip_date, description, status, published_at, photos list)
    - Add `PaginatedTrips` schema (total, page, page_size, items list of TripListItem)
    - _Requirements: 2.1, 2.4, 2.5, 5.1_

  - [x] 1.3 Create Alembic migration for `trips` and `trip_photos` tables
    - Generate migration depending on `0a32561a475e_initial_schema`
    - Create `trips` table and `trip_photos` table with foreign key and index on trip_id
    - _Requirements: 7.4_

- [x] 2. Implement public trips API endpoints
  - [x] 2.1 Create `backend/app/routers/public_trips.py` with list and detail endpoints
    - Implement `GET /api/trips` with pagination (page, page_size query params)
    - Filter by status="published", order by trip_date DESC then created_at DESC
    - Return `PaginatedTrips` with cover_photo_url from position-1 photo
    - Implement `GET /api/trips/{trip_id}` returning `TripDetail` with photos ordered by position ASC
    - Return 404 if trip not found or not published
    - _Requirements: 1.2, 1.3, 1.5, 1.6, 1.7, 3.2_

  - [x] 2.2 Register public trips router in `backend/app/main.py`
    - Import and include the `public_trips` router
    - _Requirements: 7.7_

  - [ ]* 2.3 Write property test for trip list ordering (Property 1)
    - **Property 1: Trip list ordering**
    - Use Hypothesis to generate sets of published trips with arbitrary dates and creation times
    - Assert response items are ordered by trip_date DESC, then created_at DESC
    - **Validates: Requirements 1.2, 1.3**

  - [ ]* 2.4 Write property test for trip list item fields (Property 2)
    - **Property 2: Trip list items contain required fields**
    - Use Hypothesis to generate published trips with at least one photo
    - Assert each list item includes title, trip_date, and cover_photo_url matching position-1 photo
    - **Validates: Requirements 1.5**

  - [ ]* 2.5 Write property test for trip detail fields (Property 3)
    - **Property 3: Trip detail contains required fields**
    - Use Hypothesis to generate published trips with various field combinations
    - Assert detail response includes title, trip_date, description (if present), and all photos
    - **Validates: Requirements 1.7**

  - [ ]* 2.6 Write property test for photos returned in position order (Property 5)
    - **Property 5: Photos returned in position order**
    - Use Hypothesis to generate trips with photos at arbitrary positions
    - Assert detail response photos are sorted by position ascending
    - **Validates: Requirements 3.2**

- [x] 3. Implement CMS trips API endpoints
  - [x] 3.1 Create `backend/app/routers/cms_trips.py` with CRUD endpoints
    - Implement `POST /api/cms/trips` — create trip with photos, require JWT auth
    - Implement `GET /api/cms/trips` — list all trips (drafts + published) for CMS
    - Implement `GET /api/cms/trips/{trip_id}` — get single trip (any status)
    - Implement `PUT /api/cms/trips/{trip_id}` — update trip fields and photos; delete removed photos from S3
    - Implement `DELETE /api/cms/trips/{trip_id}` — delete trip, delete all S3 photos (best-effort), return 204
    - Set published_at when status changes to "published"
    - Validate title required and trip_date required when publishing
    - _Requirements: 5.8, 5.9, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10_

  - [x] 3.2 Register CMS trips router in `backend/app/main.py`
    - Import and include the `cms_trips` router
    - _Requirements: 7.7_

  - [ ]* 3.3 Write property test for trip field validation (Property 4)
    - **Property 4: Trip field validation**
    - Use Hypothesis to generate strings of various lengths for title and description
    - Assert titles 1-150 chars accepted, >150 rejected; descriptions 0-2000 accepted, >2000 rejected; photo lists 0-20 accepted, >20 rejected
    - **Validates: Requirements 2.1, 2.4, 2.5, 5.1, 5.3**

  - [ ]* 3.4 Write property test for CMS authentication requirement (Property 8)
    - **Property 8: CMS endpoints require authentication**
    - Use Hypothesis to generate arbitrary trip data
    - Assert all CMS endpoints return 401 without valid JWT
    - **Validates: Requirements 6.10**

  - [ ]* 3.5 Write unit tests for CMS trips endpoints
    - Test create trip with valid data returns 201
    - Test create draft does not appear in public list
    - Test delete trip returns 204 and removes from DB
    - Test edit published trip updates fields correctly
    - Test publish without title returns validation error
    - Test publish without trip_date returns validation error
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.8_

- [x] 4. Checkpoint - Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement public frontend pages
  - [x] 5.1 Create `/trips` page at `frontend/app/trips/page.tsx`
    - Server-rendered page with ISR (revalidate: 60)
    - Fetch from `GET /api/trips` and render trip list
    - Display each trip as a card with title, trip_date, and cover photo thumbnail
    - Show placeholder image when trip has no photos
    - Show "no trips available" message when list is empty
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 7.1, 7.5_

  - [x] 5.2 Create `/trips/[id]` page at `frontend/app/trips/[id]/page.tsx`
    - Server-rendered page with ISR (revalidate: 60)
    - Fetch from `GET /api/trips/{id}` and render trip detail
    - Display title, trip_date, description (preserving paragraph breaks), and PhotoGallery component
    - _Requirements: 1.7, 2.3, 7.6_

  - [x] 5.3 Create `PhotoGallery` component at `frontend/components/PhotoGallery.tsx`
    - Responsive grid: 3+ columns at ≥768px, 2 columns below 768px
    - Display each photo as a square thumbnail (object-fit: cover)
    - On photo click, open Lightbox with selected photo index
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 5.4 Create `Lightbox` component at `frontend/components/Lightbox.tsx`
    - Modal overlay with dark semi-transparent backdrop
    - Display selected photo at larger size
    - Next/previous controls with wrap-around navigation
    - Close control (button + Escape key)
    - Keyboard navigation: right arrow = next, left arrow = previous
    - Do not navigate away from the page
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_

  - [ ]* 5.5 Write property test for lightbox navigation wrapping (Property 6)
    - **Property 6: Lightbox navigation wraps correctly**
    - Use fast-check to generate gallery sizes N ≥ 1 and current index i
    - Assert next produces (i + 1) % N and previous produces (i - 1 + N) % N
    - **Validates: Requirements 4.4, 4.5**

  - [ ]* 5.6 Write unit tests for PhotoGallery and Lightbox components
    - Test PhotoGallery renders correct number of images
    - Test Lightbox opens on photo click, closes on Escape/close button
    - Test keyboard navigation (arrow keys) works in lightbox
    - Test responsive grid breakpoints
    - _Requirements: 3.1, 3.3, 3.4, 4.1, 4.6, 4.7, 4.8, 4.9_

- [x] 6. Implement CMS frontend pages
  - [x] 6.1 Create `/cms/trips` page at `frontend/app/cms/trips/page.tsx`
    - Client-rendered page with JWT auth
    - List all trips with status badges (draft/published)
    - Link to create new trip and edit existing trips
    - _Requirements: 6.1, 6.10_

  - [x] 6.2 Create `TripForm` component at `frontend/components/TripForm.tsx`
    - Form fields: title (max 150 chars), trip_date (date picker), description (max 2000 chars)
    - Inline validation: title required for publish, trip_date required for publish, character limits
    - Display error messages for validation failures
    - Integrate PhotoUploader component for photo management
    - _Requirements: 2.4, 2.5, 6.1, 6.3, 6.4_

  - [x] 6.3 Create `PhotoUploader` component at `frontend/components/PhotoUploader.tsx`
    - Upload photos via presigned S3 URLs (reuse existing presign endpoint)
    - Accept only JPEG and PNG files up to 10 MB each
    - Enforce maximum of 20 photos per trip
    - Display per-file upload progress and error status
    - Drag-and-drop reordering of photos (update position values)
    - Remove photo button with confirmation
    - Show validation errors for file type, size, and count violations
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.9_

  - [x] 6.4 Create `/cms/trips/new` page at `frontend/app/cms/trips/new/page.tsx`
    - Client-rendered page with JWT auth
    - Render TripForm in create mode
    - On submit, POST to `/api/cms/trips` and redirect to trips list
    - _Requirements: 6.1, 6.2_

  - [x] 6.5 Create `/cms/trips/[id]/edit` page at `frontend/app/cms/trips/[id]/edit/page.tsx`
    - Client-rendered page with JWT auth
    - Fetch existing trip data and render TripForm in edit mode
    - On submit, PUT to `/api/cms/trips/{id}` and redirect to trips list
    - Include delete button that calls DELETE endpoint
    - _Requirements: 6.6, 6.7, 6.8_

  - [ ]* 6.6 Write property test for photo reorder positions (Property 7)
    - **Property 7: Photo reorder produces sequential positions**
    - Use fast-check to generate N photos and arbitrary permutations
    - Assert after reorder, positions are exactly 1, 2, ..., N matching new visual order
    - **Validates: Requirements 5.6**

  - [ ]* 6.7 Write unit tests for TripForm and PhotoUploader components
    - Test TripForm validates title length and shows error
    - Test PhotoUploader enforces 20-photo limit
    - Test PhotoUploader rejects non-JPEG/PNG files
    - Test PhotoUploader rejects files over 10 MB
    - _Requirements: 2.4, 2.5, 5.2, 5.3, 5.4, 5.5_

- [x] 7. Integration wiring and homepage link
  - [x] 7.1 Add "Family Trips" card to homepage at `frontend/app/page.tsx`
    - Add a clickable card linking to `/trips`
    - Match existing homepage card styling
    - _Requirements: 1.1_

  - [x] 7.2 Add "Trips" link to CMS navigation in `frontend/app/cms/layout.tsx`
    - Add navigation link to `/cms/trips` in the CMS sidebar/nav
    - _Requirements: 6.10_

  - [ ]* 7.3 Write integration tests for full trip lifecycle
    - Test create draft → edit → publish → verify in public list → delete
    - Test trip delete triggers S3 deletion for each photo
    - Test presigned URL generation works for trip photos
    - _Requirements: 6.5, 6.7, 6.9, 5.8, 5.9_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The backend uses Python (FastAPI, SQLAlchemy, Hypothesis for PBT)
- The frontend uses TypeScript (Next.js, fast-check for PBT)
- Photo upload reuses the existing `cms_photos` presign endpoint — no new S3 infrastructure needed

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["2.1", "3.1"] },
    { "id": 3, "tasks": ["2.2", "3.2"] },
    { "id": 4, "tasks": ["2.3", "2.4", "2.5", "2.6", "3.3", "3.4", "3.5"] },
    { "id": 5, "tasks": ["5.1", "5.2", "5.3", "5.4", "6.1", "6.2", "6.3"] },
    { "id": 6, "tasks": ["5.5", "5.6", "6.4", "6.5"] },
    { "id": 7, "tasks": ["6.6", "6.7", "7.1", "7.2"] },
    { "id": 8, "tasks": ["7.3"] }
  ]
}
```
