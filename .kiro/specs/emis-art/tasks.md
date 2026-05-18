# Implementation Plan: Emi's Art

## Overview

This plan implements the Emi's Art feature following the existing architectural patterns (FastAPI + SQLAlchemy backend, Next.js frontend). Work is organized as: database model → backend API → frontend public pages → frontend CMS page → homepage/nav activation → integration wiring. Each step builds incrementally on the previous one, reusing existing infrastructure (S3, CloudFront, presign endpoint, Lightbox/PhotoGallery components).

## Tasks

- [x] 1. Set up database model and migration
  - [x] 1.1 Add ArtPiece SQLAlchemy model to `backend/app/models.py`
    - Add `ArtPiece` model with fields: id, year (Integer, indexed), title (String 200, nullable), s3_key (String 512), cdn_url (String 1024), position (Integer), status (String 10, default "draft"), published_at (DateTime, nullable), created_at, updated_at
    - _Requirements: 2.1, 2.2, 8.4_

  - [x] 1.2 Add Art Pydantic schemas to `backend/app/schemas.py`
    - Add `ArtPieceCreate` schema (year ge=2020 with dynamic upper bound validation, s3_key, cdn_url, title max 200 nullable)
    - Add `ArtPieceUpdate` schema (title max 200 nullable, status literal "draft"/"published" nullable)
    - Add `ArtPieceBulkReorder` schema (year ge=2020, order list of int IDs min_length=1)
    - Add `ArtPieceOut` schema (id, cdn_url, title, position) with `from_attributes=True`
    - Add `CmsArtPieceOut` schema (id, year, s3_key, cdn_url, title, position, status) with `from_attributes=True`
    - Add `YearSummary` schema (year, cover_photo_url nullable, count)
    - Add `CmsYearGroup` schema (year, pieces list of CmsArtPieceOut)
    - _Requirements: 2.1, 2.2, 5.1, 6.1_

  - [x] 1.3 Create Alembic migration for `art_pieces` table
    - Generate migration depending on `b3f8a2c71d4e_add_trips_and_trip_photos`
    - Create `art_pieces` table with index on year column
    - _Requirements: 8.4_

- [x] 2. Implement public art API endpoints
  - [x] 2.1 Create `backend/app/routers/public_art.py` with year list and year gallery endpoints
    - Implement `GET /api/art/years` — query distinct years with at least one published art piece, return `YearSummary` list ordered by year DESC; cover_photo_url is the cdn_url of the published piece with lowest position in that year
    - Implement `GET /api/art/years/{year}` — return list of `ArtPieceOut` for published pieces in that year, ordered by position ASC; return empty array if no published pieces exist
    - _Requirements: 1.3, 1.5, 1.6, 1.7, 3.2, 8.5, 8.6_

  - [x] 2.2 Register public art router in `backend/app/main.py`
    - Import and include the `public_art` router
    - _Requirements: 8.7_

  - [ ]* 2.3 Write property test for year list filtering and ordering (Property 1)
    - **Property 1: Year list filtering and ordering**
    - Use Hypothesis to generate sets of art pieces with arbitrary years and statuses
    - Assert response contains only years with at least one published piece, ordered newest to oldest
    - **Validates: Requirements 1.3, 1.6**

  - [ ]* 2.4 Write property test for cover piece selection (Property 2)
    - **Property 2: Cover piece selection**
    - Use Hypothesis to generate year groups with multiple published pieces at arbitrary positions
    - Assert cover_photo_url matches the cdn_url of the published piece with the lowest position value
    - **Validates: Requirements 1.5**

  - [ ]* 2.5 Write property test for year gallery filtering and ordering (Property 3)
    - **Property 3: Year gallery filtering and ordering**
    - Use Hypothesis to generate art pieces with mixed statuses and arbitrary positions within a year
    - Assert response contains only published pieces, ordered by position ascending
    - **Validates: Requirements 1.7, 3.2**

- [x] 3. Implement CMS art API endpoints
  - [x] 3.1 Create `backend/app/routers/cms_art.py` with CRUD and reorder endpoints
    - Implement `GET /api/cms/art` — list all art pieces grouped by year (drafts + published), require JWT auth
    - Implement `POST /api/cms/art` — create art piece with status "draft", assign next position in year, require JWT auth; validate year range dynamically (2020 to current year)
    - Implement `PUT /api/cms/art/{art_id}` — update title/status; set published_at when publishing; reject publish if no image; require JWT auth
    - Implement `DELETE /api/cms/art/{art_id}` — delete art piece, delete S3 object (best-effort), re-sequence positions for remaining pieces in that year; require JWT auth
    - Implement `PUT /api/cms/art/reorder` — accept year + ordered list of IDs, assign positions 1..N based on array index; validate all IDs belong to specified year; require JWT auth
    - _Requirements: 5.1, 5.5, 5.6, 5.7, 5.8, 5.9, 6.1, 6.2, 6.3, 6.5, 6.7, 6.8, 6.9, 6.10_

  - [x] 3.2 Register CMS art router in `backend/app/main.py`
    - Import and include the `cms_art` router
    - _Requirements: 8.7_

  - [ ]* 3.3 Write property test for art piece field validation (Property 4)
    - **Property 4: Art piece field validation**
    - Use Hypothesis to generate year values and title strings of various lengths
    - Assert years 2020 to current year accepted, outside rejected; titles 0-200 chars accepted, >200 rejected
    - **Validates: Requirements 2.1, 2.5, 2.6**

  - [ ]* 3.4 Write property test for position contiguity after mutations (Property 6)
    - **Property 6: Position contiguity after mutations**
    - Use Hypothesis to generate year groups and apply create/delete/reorder operations
    - Assert positions always form contiguous sequence 1..M after any mutation
    - **Validates: Requirements 5.5, 5.7, 6.2**

  - [ ]* 3.5 Write property test for CMS authentication requirement (Property 7)
    - **Property 7: CMS endpoints require authentication**
    - Use Hypothesis to generate arbitrary art data
    - Assert all CMS endpoints return 401 without valid JWT
    - **Validates: Requirements 6.9**

  - [ ]* 3.6 Write unit tests for CMS art endpoints
    - Test create art piece returns 201 with status "draft" and correct position
    - Test create assigns next position (appended after last piece in year)
    - Test delete returns 204, removes from DB, and re-sequences positions
    - Test publish sets published_at timestamp
    - Test publish without image returns validation error
    - Test update title on published piece works correctly
    - Test reorder with invalid IDs returns 400
    - _Requirements: 5.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8_

- [x] 4. Checkpoint - Backend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement public frontend pages
  - [x] 5.1 Create `/art` page at `frontend/app/art/page.tsx`
    - Server-rendered page with ISR (revalidate: 60)
    - Fetch from `GET /api/art/years` and render year list
    - Display each year as a card with year number and cover photo thumbnail
    - Show "no art available yet" message when list is empty
    - Provide navigation back to homepage
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 8.1, 8.5_

  - [x] 5.2 Create `/art/[year]` page at `frontend/app/art/[year]/page.tsx`
    - Server-rendered page with ISR (revalidate: 60)
    - Fetch from `GET /api/art/years/{year}` and render year gallery
    - Display year number as heading above the grid
    - Responsive grid: 3+ columns at ≥768px, 2 columns below 768px
    - Display each art piece as a square thumbnail (object-fit: cover)
    - Render title below thumbnail when present, no caption when absent
    - Show "no art available for this year" message with link back to year list when empty
    - Provide navigation link back to year list
    - On thumbnail click, open Lightbox with selected piece
    - _Requirements: 1.7, 1.8, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 8.6_

  - [x] 5.3 Enhance `Lightbox` component to support optional title display
    - Add optional `title?: string` to the photo interface used by Lightbox
    - Render title below the image when present
    - Ensure existing Lightbox behavior (navigation, keyboard, accessibility, focus trap, aria-modal) remains intact
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 4.13_

  - [ ]* 5.4 Write property test for lightbox navigation wrapping (Property 5)
    - **Property 5: Lightbox navigation wraps correctly**
    - Use fast-check to generate gallery sizes N ≥ 1 and current index i
    - Assert next produces (i + 1) % N and previous produces (i - 1 + N) % N
    - **Validates: Requirements 4.4, 4.5**

  - [ ]* 5.5 Write unit tests for art public pages and Lightbox title
    - Test ArtYearsPage renders year cards with cover thumbnails
    - Test ArtYearGalleryPage renders responsive grid
    - Test gallery thumbnails are square (aspect-square + object-cover)
    - Test Lightbox displays title below image when present
    - Test Lightbox does not display title area when title is absent
    - Test Lightbox keyboard navigation (Escape, ArrowLeft, ArrowRight)
    - Test Lightbox focus trapping and aria-modal attribute
    - _Requirements: 1.3, 1.5, 3.1, 3.3, 3.4, 3.5, 4.7, 4.8, 4.9, 4.11, 4.13_

- [x] 6. Implement CMS frontend page
  - [x] 6.1 Create `/cms/art` page at `frontend/app/cms/art/page.tsx`
    - Client-rendered page with JWT auth
    - Display art pieces grouped by year (newest year first), showing both draft and published pieces with status badges
    - Year selector/form to create new art pieces for a specific year (validate year range 2020 to current year)
    - Upload widget: file picker accepting JPEG/PNG only, max 10 MB, with presigned URL upload via existing endpoint
    - Inline title editing (max 200 chars with validation error display)
    - Publish/unpublish toggle per piece
    - Delete button with confirmation prompt per piece
    - Drag-and-drop reorder within each year group (calls bulk reorder endpoint)
    - Display error messages for upload failures, validation errors
    - Show placeholder when CDN images fail to load
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.8, 5.9, 5.10, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 8.9_

  - [ ]* 6.2 Write unit tests for CMS art page
    - Test CMS page groups pieces by year
    - Test upload validates file type (JPEG/PNG only) and rejects others
    - Test upload validates file size (≤10 MB) and rejects larger
    - Test title input enforces 200-character limit with error message
    - Test year input rejects values outside 2020 to current year
    - Test delete shows confirmation prompt before executing
    - _Requirements: 5.2, 5.3, 5.4, 5.9, 6.7, 2.5, 2.6_

- [x] 7. Homepage and navigation activation
  - [x] 7.1 Activate "Emi's Art" card on homepage at `frontend/app/page.tsx`
    - Make the existing placeholder card a clickable link navigating to `/art`
    - Apply violet color scheme (violet border, violet background) with hover states (darkened border and shadow)
    - Use active text colors (not grayed out) with descriptive subtitle
    - _Requirements: 7.1, 7.3_

  - [x] 7.2 Activate "Emi's Art" link in navigation bar
    - Make the existing placeholder link a clickable link navigating to `/art`
    - Style with violet text color and hover background consistent with other nav links
    - _Requirements: 7.2_

  - [x] 7.3 Add "Art" link to CMS navigation in `frontend/app/cms/layout.tsx`
    - Add navigation link to `/cms/art` in the CMS sidebar/nav
    - _Requirements: 6.10_

- [ ] 8. Integration wiring and final verification
  - [ ]* 8.1 Write integration tests for full art lifecycle
    - Test create draft → edit title → publish → verify in public year gallery → delete
    - Test art piece delete triggers S3 deletion for the piece's key
    - Test reorder → verify positions updated correctly in DB
    - Test presigned URL generation works for art photos (reuses existing endpoint)
    - _Requirements: 6.3, 6.5, 6.7, 6.8, 5.7, 5.8_

- [x] 9. Final checkpoint - Ensure all tests pass
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
- The existing `Lightbox` component is enhanced (not replaced) with an optional title prop
- CMS art management is a single page (unlike trips which has separate list/new/edit pages) since art management is simpler

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["2.1", "3.1"] },
    { "id": 3, "tasks": ["2.2", "3.2"] },
    { "id": 4, "tasks": ["2.3", "2.4", "2.5", "3.3", "3.4", "3.5", "3.6"] },
    { "id": 5, "tasks": ["5.1", "5.2", "5.3", "6.1"] },
    { "id": 6, "tasks": ["5.4", "5.5", "6.2", "7.1", "7.2", "7.3"] },
    { "id": 7, "tasks": ["8.1"] }
  ]
}
```
