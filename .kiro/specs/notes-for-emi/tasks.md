# Implementation Plan: Notes for Emi

## Overview

Implement the "Notes for Emi" feature as a full-stack application: a FastAPI backend with SQLite, a Next.js frontend with Tiptap, photo storage on AWS S3/CloudFront, and deployment via Coolify on an Oracle VM. Tasks are ordered by dependency — data layer first, then API, then frontend, then deployment configuration.

## Tasks

- [x] 1. Backend project scaffold and database layer
  - [x] 1.1 Initialise the backend Python project
    - Create `backend/` directory with `pyproject.toml` (or `requirements.txt`) listing: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `pydantic[email]`, `python-jose[cryptography]`, `bcrypt`, `boto3`, `nh3`, `hypothesis`, `pytest`, `httpx`, `pytest-asyncio`
    - Add `backend/app/__init__.py`, `backend/app/main.py` (bare FastAPI app), and `backend/app/config.py` (reads env vars: `CMS_PASSWORD_HASH`, `JWT_SECRET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET`, `CLOUDFRONT_DOMAIN`)
    - Add `.env.example` with all required variable names (no values)
    - _Requirements: 6.4_

  - [x] 1.2 Define SQLAlchemy models and Alembic migrations
    - Create `backend/app/models.py` with `Note`, `Label`, `NoteLabel`, and `Photo` SQLAlchemy ORM models matching the data model in the design (columns, types, constraints, ON DELETE CASCADE)
    - Enable SQLite WAL mode in the engine creation (`PRAGMA journal_mode=WAL`)
    - Initialise Alembic (`alembic init alembic/`) and write the initial migration that creates all four tables
    - _Requirements: 2.1, 2.2, 3.1, 4.1_

  - [ ]* 1.3 Write property test for Note field validation constraints (Property 4)
    - **Property 4: Note field validation enforces all structural constraints**
    - Use `hypothesis.strategies` to generate boundary-crossing combinations of title length, body length, label count/length, and photo count
    - Assert that the Pydantic `NoteCreate` schema accepts valid inputs and raises `ValidationError` for any constraint violation
    - **Validates: Requirements 2.1, 2.2, 3.1, 4.1, 4.3**

- [x] 2. Pydantic schemas and core utilities
  - [x] 2.1 Implement Pydantic request and response schemas
    - Create `backend/app/schemas.py` with all schemas from the design: `LabelOut`, `PhotoOut`, `PhotoIn`, `NoteListItem`, `NoteDetail`, `NoteCreate`, `NoteUpdate`, `PaginatedNotes`, `PresignRequest`, `PresignResponse`, `LoginRequest`, `TokenResponse`
    - Add `Field` constraints matching the design (title 1–100, body 1–50 000, labels max 20, photos max 2, position 1–2)
    - _Requirements: 2.1, 2.2, 3.1, 4.1, 4.3_

  - [x] 2.2 Implement excerpt generation and HTML sanitisation utilities
    - Create `backend/app/utils.py`
    - Implement `generate_excerpt(body_html: str) -> str`: strips HTML tags using `html.parser`, truncates plain text to 200 characters
    - Implement `sanitise_html(body_html: str) -> str`: uses `nh3` to allow only the Tiptap-produced tags (p, strong, em, h1–h3, ul, ol, li, img with src/class/alt attributes)
    - _Requirements: 1.4, 2.3_

  - [ ]* 2.3 Write property test for excerpt generation (Property 2)
    - **Property 2: Note_List items contain all required fields with correct excerpt**
    - Generate arbitrary HTML strings with `hypothesis`; assert that `generate_excerpt` always returns a string of at most 200 characters and that the result equals the full plain-text body when the plain-text body is ≤ 200 characters
    - **Validates: Requirements 1.4**

  - [x] 2.4 Implement label normalisation utility
    - In `backend/app/utils.py`, implement `normalise_labels(labels: list[str]) -> list[str]`: strips whitespace, lowercases, deduplicates (preserving first occurrence order)
    - _Requirements: 4.6_

  - [ ]* 2.5 Write property test for label deduplication (Property 8)
    - **Property 8: Label deduplication preserves exactly one instance per unique label (case-insensitive)**
    - Generate lists of label strings including duplicates in varying cases; assert that `normalise_labels` output contains no two entries that are equal under case-insensitive comparison
    - **Validates: Requirements 4.6**

- [x] 3. Authentication
  - [x] 3.1 Implement JWT auth utilities and login endpoint
    - Create `backend/app/auth.py` with `create_access_token(sub: str, expires_delta: timedelta) -> str` and `verify_token(token: str) -> dict` using `python-jose` (HS256, 24-hour expiry)
    - Implement `verify_password(plain: str, hashed: str) -> bool` using `bcrypt`
    - Create `backend/app/routers/auth.py` with `POST /api/cms/auth/login`: reads `CMS_PASSWORD_HASH` from config, verifies password, returns `TokenResponse`
    - Add a FastAPI `Depends` function `get_current_author` that validates the `Authorization: Bearer` header on CMS routes
    - _Requirements: 6.8_

  - [ ]* 3.2 Write property test for JWT auth rejection (Property 10)
    - **Property 10: All CMS mutation endpoints reject requests without a valid JWT**
    - Generate arbitrary strings as Bearer tokens; assert that every CMS mutation endpoint returns `401` for any token that is not a currently valid JWT signed with the server secret
    - **Validates: Requirements 6.8**

- [x] 4. Public API endpoints
  - [x] 4.1 Implement `GET /api/notes` (paginated note list)
    - Create `backend/app/routers/public.py`
    - Query only `status = 'published'` notes, ordered by `published_at DESC`, then `created_at DESC`
    - Apply `page` / `page_size` pagination (default 1 / 20, max page_size 50)
    - Build `NoteListItem` responses using `generate_excerpt` for each note
    - Return `PaginatedNotes` response
    - _Requirements: 1.2, 1.4_

  - [ ]* 4.2 Write property test for Note_List ordering (Property 1)
    - **Property 1: Note_List is always ordered newest-first**
    - Insert an arbitrary set of published notes with random `published_at` timestamps (including ties broken by `created_at`); assert that the `GET /api/notes` response items are in non-increasing `published_at` order with ties resolved by `created_at` descending
    - **Validates: Requirements 1.2**

  - [x] 4.3 Implement `GET /api/notes/{id}` (note detail)
    - In `backend/app/routers/public.py`, add the detail endpoint
    - Return `404` if the note does not exist or `status != 'published'`
    - Build `NoteDetail` response including labels and photos ordered by `position ASC`
    - _Requirements: 1.5, 3.3_

  - [ ]* 4.4 Write property test for Note_Detail completeness (Property 3)
    - **Property 3: Note detail response contains all attached content**
    - For arbitrary combinations of 0–2 photos and 0–20 labels, assert that `GET /api/notes/{id}` returns all label names and all photo `cdn_url` values with correct positions
    - **Validates: Requirements 1.5, 4.4**

  - [ ]* 4.5 Write property test for photo position ordering (Property 7)
    - **Property 7: Photos in note detail are ordered by position ascending**
    - Store notes with photos in arbitrary position order; assert that the response always returns photos sorted by `position` ascending
    - **Validates: Requirements 3.3**

- [x] 5. CMS note CRUD endpoints
  - [x] 5.1 Implement `POST /api/cms/notes` (create note)
    - Create `backend/app/routers/cms_notes.py` with `get_current_author` dependency on all routes
    - Sanitise `body_html` with `sanitise_html` before persisting
    - Run `normalise_labels` on submitted labels; upsert labels; associate with note
    - If `status = 'published'` and `published_at` is null, set `published_at = now()`
    - Return `201` with the created note
    - _Requirements: 5.1, 5.2, 4.6_

  - [x] 5.2 Implement `GET /api/cms/notes` and `GET /api/cms/notes/{id}`
    - List all notes (drafts + published), ordered by `created_at DESC`
    - Detail endpoint returns note regardless of status (draft or published)
    - _Requirements: 5.2_

  - [x] 5.3 Implement `PUT /api/cms/notes/{id}` (update note)
    - Replace labels and photos with submitted lists (delete old associations, insert new)
    - If transitioning from `draft` to `published` and `published_at` is null, set `published_at = now()`
    - Sanitise `body_html` before persisting
    - _Requirements: 5.5, 5.6_

  - [x] 5.4 Implement `DELETE /api/cms/notes/{id}`
    - Delete the note row; cascade deletes `NoteLabel` and `Photo` rows automatically
    - Return `204 No Content`
    - _Requirements: 5.7_

  - [ ]* 5.5 Write property test for write-read consistency (Property 9)
    - **Property 9: Write operations are immediately reflected in read responses**
    - For arbitrary valid note payloads: assert publish makes note appear in `GET /api/notes`; assert update is reflected in `GET /api/notes/{id}`; assert delete returns `404` from `GET /api/notes/{id}`
    - **Validates: Requirements 5.4, 5.6, 5.8**

  - [ ]* 5.6 Write property test for body HTML round-trip (Property 5)
    - **Property 5: Body HTML is preserved through a write-read round trip**
    - Generate valid Tiptap-like HTML strings (p, strong, em, h1–h3, ul, ol, li elements); store via `POST /api/cms/notes` and retrieve via `GET /api/notes/{id}`; assert the returned `body_html` is semantically equivalent after normalisation
    - **Validates: Requirements 2.3**

- [x] 6. Photo presign and delete endpoints
  - [x] 6.1 Implement `POST /api/cms/photos/presign`
    - Create `backend/app/routers/cms_photos.py`
    - Validate `content_type` is `image/jpeg` or `image/png`; return `400` otherwise
    - Generate S3 key as `photos/{year}/{uuid4}.{ext}`
    - Call `boto3` `generate_presigned_url` with `ExpiresIn=900` (15 min), method `put_object`
    - Construct `cdn_url` as `https://{CLOUDFRONT_DOMAIN}/{s3_key}`
    - Return `PresignResponse`
    - _Requirements: 3.2, 3.6, 6.5_

  - [ ]* 6.2 Write property test for presign content-type validation (Property 6)
    - **Property 6: Photo presign endpoint accepts only JPEG and PNG content types**
    - Generate arbitrary `content_type` strings; assert the endpoint returns a presigned URL for `"image/jpeg"` and `"image/png"` only, and `400` for all other values
    - **Validates: Requirements 3.2, 3.6**

  - [x] 6.3 Implement `DELETE /api/cms/photos/{key}` (S3 delete)
    - URL-decode the `key` path parameter
    - Call `boto3` `delete_object` on the S3 bucket
    - Return `204 No Content`
    - _Requirements: 6.5_

- [x] 7. Backend integration and wiring
  - [x] 7.1 Register all routers and configure CORS in `main.py`
    - Mount `public` router at `/api`, `auth` router at `/api/cms/auth`, `cms_notes` router at `/api/cms`, `cms_photos` router at `/api/cms`
    - Add CORS middleware allowing the frontend origin
    - Add a startup event that runs `alembic upgrade head` (or creates tables directly) on first boot
    - _Requirements: 6.4_

  - [x] 7.2 Write backend integration tests
    - In `backend/tests/test_integration.py`, use `pytest` + `httpx.AsyncClient` with an in-memory SQLite test database
    - Cover: full CRUD lifecycle (create draft → publish → edit → delete); auth (valid login, wrong password, missing token, expired token); photo presign (valid types, invalid type, third photo rejected); public API (published notes appear, drafts do not)
    - _Requirements: 5.1–5.8, 6.8, 3.1–3.2_

  - [x] 7.3 Write backend Dockerfile
    - `backend/Dockerfile`: Python 3.12 slim base, install dependencies, copy app, expose port 8000, `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
    - _Requirements: 6.4_

- [x] 8. Checkpoint — backend tests pass
  - Run `pytest backend/` and ensure all tests pass. Ask the user if any questions arise before proceeding to the frontend.

- [x] 9. Frontend project scaffold
  - [x] 9.1 Initialise the Next.js project
    - Create `frontend/` with `npx create-next-app@latest` (TypeScript, App Router, Tailwind CSS)
    - Install additional dependencies: `@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/extension-image`, `vitest`, `@vitejs/plugin-react`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`
    - Configure `vitest.config.ts` with jsdom environment and React Testing Library setup
    - Add `NEXT_PUBLIC_API_URL` and `REVALIDATE_SECRET` to `.env.local.example`
    - _Requirements: 6.4_

  - [x] 9.2 Implement shared layout and navigation
    - Create `frontend/app/layout.tsx` with a top-level `<nav>` containing a visible link to `/notes` labelled "Notes for Emi"
    - Apply global CSS including the `.note-photo`, `.note-photo--float-left`, `.note-photo--float-right`, and `.note-body::after` clearfix styles from the design, plus the mobile media query that removes floats at ≤ 640 px
    - _Requirements: 1.1, 3.3_

- [x] 10. Public frontend pages
  - [x] 10.1 Implement the Note_List page (`/notes`)
    - Create `frontend/app/notes/page.tsx` as an ISR page (`revalidate: 60`)
    - Fetch `GET /api/notes` from the FastAPI backend (server-side)
    - Render a card per note showing title, `published_at`, excerpt, and label chips
    - When the list is empty, display "No notes yet — check back soon."
    - _Requirements: 1.2, 1.3, 1.4_

  - [ ]* 10.2 Write Vitest tests for Note_List rendering
    - Test that the component renders title, date, excerpt, and labels for a mocked note list
    - Test that the empty-state message appears when the list is empty
    - _Requirements: 1.3, 1.4_

  - [x] 10.3 Implement the Note_Detail page (`/notes/[id]`)
    - Create `frontend/app/notes/[id]/page.tsx` as an ISR page
    - Fetch `GET /api/notes/{id}`; render `body_html` via `dangerouslySetInnerHTML` inside a `<div className="note-body">`
    - Display `published_at` and label chips
    - Return Next.js `notFound()` on 404
    - _Requirements: 1.5, 2.3, 3.3, 3.4, 3.5_

  - [ ]* 10.4 Write Vitest tests for Note_Detail rendering
    - Test that `body_html` is rendered, labels are shown, and photos with float classes appear
    - Test that placeholder slots for missing photos are not rendered
    - _Requirements: 1.5, 3.4, 3.5_

- [x] 11. CMS authentication
  - [x] 11.1 Implement the CMS login page (`/cms`)
    - Create `frontend/app/cms/page.tsx` with a password form
    - On submit, call `POST /api/cms/auth/login`; on success, store the JWT in `localStorage` and redirect to `/cms/notes`
    - On failure, display an inline error message
    - _Requirements: 6.8_

  - [x] 11.2 Implement CMS auth guard
    - Create `frontend/app/cms/layout.tsx` that reads the JWT from `localStorage` on mount; if absent or expired, redirects to `/cms`
    - _Requirements: 6.8_

- [x] 12. CMS note management pages
  - [x] 12.1 Implement the CMS note list page (`/cms/notes`)
    - Create `frontend/app/cms/notes/page.tsx` (client component)
    - Fetch `GET /api/cms/notes` with the JWT Bearer header
    - Display all notes (drafts + published) with Edit and Delete buttons
    - Delete button calls `DELETE /api/cms/notes/{id}` and refreshes the list
    - _Requirements: 5.7_

  - [x] 12.2 Implement the Tiptap rich-text editor component
    - Create `frontend/components/NoteEditor.tsx`
    - Configure Tiptap with `StarterKit` (bold, italic, headings h1–h3, bullet list, ordered list) and a custom `Image` extension that supports a `float` attribute (`left` | `right`)
    - The Image extension renders `<img>` with `class="note-photo note-photo--float-{float}"` and `alt=""`
    - Expose `content` (HTML string) and `onChange` props
    - _Requirements: 2.3, 3.3_

  - [x] 12.3 Implement the photo upload component
    - Create `frontend/components/PhotoUpload.tsx`
    - Accept up to 2 photos; validate MIME type (`image/jpeg`, `image/png`) and file size (≤ 10 MB) client-side before requesting a presign URL
    - Call `POST /api/cms/photos/presign`, then PUT the file directly to the returned `upload_url`
    - After upload, store `{ s3_key, cdn_url, position }` in parent form state
    - Disable the upload button once 2 photos are attached; show an error if a third is attempted
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 3.6_

  - [x] 12.4 Implement the label input component
    - Create `frontend/components/LabelInput.tsx`
    - Allow adding labels up to the 20-label maximum; disable the add input after 20 labels
    - Validate each label: non-empty, ≤ 50 characters; show inline error otherwise
    - Detect case-insensitive duplicates and show a warning without adding the duplicate
    - Allow removing labels
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6_

  - [x] 12.5 Implement the new note form page (`/cms/notes/new`)
    - Create `frontend/app/cms/notes/new/page.tsx` (client component)
    - Compose `NoteEditor`, `PhotoUpload`, and `LabelInput` components
    - Title input with max 100 characters; show inline error if empty on publish attempt
    - Save as Draft button calls `POST /api/cms/notes` with `status: "draft"`
    - Publish button calls `POST /api/cms/notes` with `status: "published"`; on success, triggers ISR revalidation via `POST /api/revalidate` with `REVALIDATE_SECRET`
    - Display inline error if body exceeds 50 000 characters without discarding content
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 2.6_

  - [x] 12.6 Implement the edit note form page (`/cms/notes/[id]/edit`)
    - Create `frontend/app/cms/notes/[id]/edit/page.tsx` (client component)
    - Load existing note via `GET /api/cms/notes/{id}` and pre-populate all fields
    - Save and Publish buttons call `PUT /api/cms/notes/{id}`; on success, trigger ISR revalidation
    - _Requirements: 5.5, 5.6_

  - [ ]* 12.7 Write Vitest tests for CMS form validation
    - Test that submitting with an empty title shows an error
    - Test that a body over 50 000 characters shows an error and does not discard content
    - Test that the label input shows a duplicate warning and does not add the duplicate
    - Test that the photo upload slot is disabled after 2 photos
    - _Requirements: 5.3, 2.6, 4.6, 3.4_

- [x] 13. Next.js ISR revalidation endpoint
  - [x] 13.1 Implement the on-demand revalidation API route
    - Create `frontend/app/api/revalidate/route.ts`
    - Accept `POST` with a `secret` query param; compare against `REVALIDATE_SECRET` env var
    - Call `revalidatePath('/notes')` and `revalidatePath('/notes/[id]', 'page')` on success
    - Return `200` on success, `401` on wrong secret
    - _Requirements: 5.4, 5.6_

- [x] 14. Frontend Dockerfile and build
  - [x] 14.1 Write frontend Dockerfile
    - `frontend/Dockerfile`: multi-stage build — Node 20 Alpine builder stage runs `next build`; runner stage copies `.next/standalone` output, exposes port 3000, `CMD ["node", "server.js"]`
    - Add `output: 'standalone'` to `next.config.js`
    - _Requirements: 6.4_

- [x] 15. Checkpoint — frontend tests pass
  - Run `npx vitest --run` inside `frontend/` and ensure all tests pass. Ask the user if any questions arise before proceeding to deployment configuration.

- [x] 16. Deployment configuration
  - [x] 16.1 Write the database backup script
    - Create `scripts/backup.sh`: runs `sqlite3 /data/emisofia.db ".backup /tmp/emisofia-$(date +%Y%m%d).db"`, uploads to `s3://emisofia-backups/db/` via `aws s3 cp`, then removes the temp file
    - Write `scripts/Dockerfile.backup`: Alpine image with `sqlite` and `awscli` installed, copies `backup.sh`, sets a cron entry to run daily
    - _Requirements: 6.5_

  - [x] 16.2 Write Coolify deployment documentation
    - Create `docs/coolify-setup.md` documenting: connecting the repository in Coolify; creating the `backend` service (build context `./backend`, port 8000, persistent volume at `/data/emisofia.db`); creating the `frontend` service (build context `./frontend`, port 3000); configuring domain routing (`/api/*` → backend, `/*` → frontend); setting all required environment variables via Coolify UI; enabling auto-redeploy on push
    - _Requirements: 6.1, 6.4, 6.7, 6.9_

- [x] 17. Final checkpoint — all tests pass
  - Run `pytest backend/` and `npx vitest --run` (in `frontend/`). Ensure all tests pass. Ask the user if any questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property-based tests use Hypothesis (`@settings(max_examples=100)`) for the backend and Vitest for the frontend
- Checkpoints at tasks 8, 15, and 17 ensure incremental validation before moving to the next layer
- The `REVALIDATE_SECRET` env var must be set in both the frontend service (Next.js reads it) and used by the CMS when calling the revalidation endpoint
- The SQLite database file path inside the container is `/data/emisofia.db`; the Coolify persistent volume must be mounted at `/data`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["1.3", "2.2", "3.1"] },
    { "id": 3, "tasks": ["2.3", "2.4", "3.2", "4.1"] },
    { "id": 4, "tasks": ["2.5", "4.2", "4.3", "5.1"] },
    { "id": 5, "tasks": ["4.4", "4.5", "5.2", "5.3", "6.1"] },
    { "id": 6, "tasks": ["5.4", "5.5", "5.6", "6.2", "6.3"] },
    { "id": 7, "tasks": ["7.1"] },
    { "id": 8, "tasks": ["7.2", "7.3"] },
    { "id": 9, "tasks": ["9.1"] },
    { "id": 10, "tasks": ["9.2", "11.1"] },
    { "id": 11, "tasks": ["10.1", "11.2", "12.2", "12.3", "12.4"] },
    { "id": 12, "tasks": ["10.2", "10.3", "12.1", "12.5"] },
    { "id": 13, "tasks": ["10.4", "12.6", "13.1"] },
    { "id": 14, "tasks": ["12.7", "14.1"] },
    { "id": 15, "tasks": ["16.1", "16.2"] }
  ]
}
```
