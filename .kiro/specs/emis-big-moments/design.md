# Design Document: Emi's Big Moments

## Overview

"Emi's Big Moments" adds a new content section to emisofia.com for documenting significant moments in Emi's life. Each moment consists of a title, date, description, and up to 2 photos displayed inline (no lightbox). The feature follows the same architectural patterns as the existing "Family Trips" section: FastAPI backend with SQLite storage, S3/CloudFront for photos, Next.js frontend with server-side rendering and 60-second revalidation, and JWT-protected CMS management.

The key difference from trips is simplicity: moments have a maximum of 2 photos (vs 20 for trips), photos are displayed inline at full width rather than in a gallery/lightbox, and descriptions are required (1-2000 chars) rather than optional.

## Architecture

```mermaid
graph TD
    subgraph Frontend [Next.js Frontend]
        HP[Homepage Card]
        ML[/moments - Moment List]
        MD[/moments/:id - Moment Detail]
        CL[/cms/moments - CMS List]
        CF[/cms/moments/new - Create Form]
        CE[/cms/moments/:id/edit - Edit Form]
    end

    subgraph Backend [FastAPI Backend]
        PUB[Public Router: /api/moments]
        CMS[CMS Router: /api/cms/moments]
        PHO[CMS Photos: /api/cms/photos/presign]
        AUTH[JWT Auth Middleware]
    end

    subgraph Storage
        DB[(SQLite - moments + moment_photos)]
        S3[AWS S3 - Photo Files]
        CF_CDN[CloudFront CDN]
    end

    HP --> ML
    ML --> PUB
    MD --> PUB
    CL --> CMS
    CF --> CMS
    CE --> CMS
    CF --> PHO
    CE --> PHO
    CMS --> AUTH
    PUB --> DB
    CMS --> DB
    CMS --> S3
    PHO --> S3
    S3 --> CF_CDN
    CF_CDN --> MD
    CF_CDN --> ML
```

The architecture mirrors the trips section exactly:
- **Public endpoints** serve published moments without authentication
- **CMS endpoints** require JWT authentication for CRUD operations
- **Photo upload** reuses the existing `/api/cms/photos/presign` endpoint
- **Photo storage** uses S3 with CloudFront CDN delivery
- **Database** adds two new tables (`moments`, `moment_photos`) to the existing SQLite database

## Components and Interfaces

### Backend Components

#### 1. Database Models (`app/models.py`)

Two new SQLAlchemy models following the Trip/TripPhoto pattern:

- **Moment** — stores moment metadata (title, date, description, status, timestamps)
- **MomentPhoto** — stores photo references (s3_key, cdn_url, position) with FK to Moment

#### 2. Pydantic Schemas (`app/schemas.py`)

Request/response schemas following existing patterns:

- **MomentPhotoIn** — CMS input for photo reference (s3_key, cdn_url, position 1-2)
- **MomentPhotoOut** — Public photo output (cdn_url, position)
- **CmsMomentPhotoOut** — CMS photo output (includes s3_key)
- **MomentListItem** — Public list item (id, title, moment_date, cover_photo_url)
- **MomentDetail** — Public detail (id, title, moment_date, description, photos)
- **CmsMomentDetail** — CMS detail (includes status, published_at, s3_keys)
- **MomentCreate** — Create payload (title, moment_date, description, status, photos)
- **MomentUpdate** — Update payload (all fields optional for partial updates)
- **PaginatedMoments** — Paginated list wrapper

#### 3. Public Router (`app/routers/public_moments.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/moments` | GET | Paginated list of published moments, ordered by date desc then created_at desc |
| `/api/moments/{id}` | GET | Single published moment detail, 404 if not found or draft |

#### 4. CMS Router (`app/routers/cms_moments.py`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/cms/moments` | GET | JWT | List all moments (drafts + published), ordered by date desc |
| `/api/cms/moments` | POST | JWT | Create a new moment |
| `/api/cms/moments/{id}` | GET | JWT | Get single moment (any status) |
| `/api/cms/moments/{id}` | PUT | JWT | Update a moment (partial update semantics) |
| `/api/cms/moments/{id}` | DELETE | JWT | Delete a moment and all associated photos |

#### 5. Alembic Migration

New migration adding `moments` and `moment_photos` tables, following the pattern of `b3f8a2c71d4e_add_trips_and_trip_photos.py`.

### Frontend Components

#### 6. Public Pages

- **`/moments` (page.tsx)** — Server-rendered list page with 60s revalidation. Displays grid of moment cards with cover photo, title, and date. Shows empty state message when no moments exist.
- **`/moments/[id]` (page.tsx)** — Server-rendered detail page. Displays title, date, description (with preserved line breaks), and photos inline at full width. Calls `notFound()` for missing/draft moments.

#### 7. CMS Pages

- **`/cms/moments` (page.tsx)** — Client-rendered list with table view (title, status, date, actions). Delete with confirmation dialog.
- **`/cms/moments/new` (page.tsx)** — Create form using shared MomentForm component.
- **`/cms/moments/[id]/edit` (page.tsx)** — Edit form using shared MomentForm component.

#### 8. Shared Components

- **`MomentForm`** — Reusable form component for create/edit. Handles title input (1-150 chars), date picker, description textarea (1-2000 chars), photo upload (max 2, JPEG/PNG, 10MB limit), drag-and-drop reorder, photo removal. Validates constraints client-side before submission.

#### 9. Navigation Updates

- **`layout.tsx`** — Add "Emi's Big Moments" link to nav bar (pink/rose color theme)
- **`page.tsx` (homepage)** — Add moments card to the homepage grid

## Data Models

### Database Schema

```sql
CREATE TABLE moments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(150) NOT NULL,
    moment_date DATE NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'draft',
    published_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE moment_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    moment_id INTEGER NOT NULL,
    s3_key VARCHAR(512) NOT NULL,
    cdn_url VARCHAR(1024) NOT NULL,
    position INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (moment_id) REFERENCES moments(id) ON DELETE CASCADE
);

CREATE INDEX ix_moment_photos_moment_id ON moment_photos(moment_id);
```

### Pydantic Schema Definitions

```python
# Input schemas
class MomentPhotoIn(BaseModel):
    s3_key: str
    cdn_url: str
    position: int = Field(ge=1, le=2)

class MomentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    moment_date: date
    description: str = Field(min_length=1, max_length=2000)
    status: Literal["draft", "published"] = "draft"
    photos: list[MomentPhotoIn] = Field(default=[], max_length=2)

class MomentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    moment_date: date | None = None
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    status: Literal["draft", "published"] | None = None
    photos: list[MomentPhotoIn] | None = Field(default=None, max_length=2)

# Output schemas
class MomentListItem(BaseModel):
    id: int
    title: str
    moment_date: date
    cover_photo_url: str | None = None

class MomentDetail(BaseModel):
    id: int
    title: str
    moment_date: date
    description: str
    photos: list[MomentPhotoOut]

class CmsMomentDetail(BaseModel):
    id: int
    title: str
    moment_date: date
    description: str
    status: str
    published_at: datetime | None = None
    photos: list[CmsMomentPhotoOut]
```

### API Response Examples

**GET /api/moments** (public list):
```json
{
  "total": 5,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 3,
      "title": "First Steps",
      "moment_date": "2025-03-15",
      "cover_photo_url": "https://cdn.emisofia.com/photos/2025/abc123.jpg"
    }
  ]
}
```

**GET /api/moments/3** (public detail):
```json
{
  "id": 3,
  "title": "First Steps",
  "moment_date": "2025-03-15",
  "description": "Today Emi took her first steps!\n\nShe was so proud of herself.",
  "photos": [
    { "cdn_url": "https://cdn.emisofia.com/photos/2025/abc123.jpg", "position": 1 },
    { "cdn_url": "https://cdn.emisofia.com/photos/2025/def456.jpg", "position": 2 }
  ]
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Moment list ordering

*For any* set of published moments, the public list endpoint SHALL return them ordered by moment_date descending, with ties broken by created_at descending (newest first).

**Validates: Requirements 1.3, 1.4**

### Property 2: List item contains cover photo from position 1

*For any* published moment with photos, the list endpoint SHALL return a cover_photo_url equal to the cdn_url of the photo at position 1. For any moment without photos, cover_photo_url SHALL be null.

**Validates: Requirements 1.6, 1.7**

### Property 3: Detail response completeness with photo ordering

*For any* published moment, the detail endpoint SHALL return the moment's title, moment_date, description, and all photos ordered by position ascending.

**Validates: Requirements 1.8, 3.2**

### Property 4: Input validation boundaries

*For any* string of length outside [1, 150] used as a title, the create/update endpoint SHALL reject it. *For any* string of length within [1, 150], it SHALL be accepted. The same applies to descriptions with bounds [1, 2000]. *For any* photos list with more than 2 items, the endpoint SHALL reject it.

**Validates: Requirements 2.1, 2.4, 2.5, 4.1, 4.3, 5.3, 5.5**

### Property 5: Photo position integrity after removal

*For any* moment with N photos (where N is 1 or 2), after removing a photo and saving, the remaining photos SHALL have sequential position values starting from 1 with no gaps.

**Validates: Requirements 4.8**

### Property 6: Cascade deletion completeness

*For any* moment with associated photos, deleting the moment SHALL result in zero photo records referencing that moment_id in the database, and all associated S3 keys SHALL have delete requests issued.

**Validates: Requirements 5.11**

## Error Handling

### Backend Error Responses

| Scenario | HTTP Status | Response Body |
|----------|-------------|---------------|
| Moment not found (public) | 404 | `{"detail": "Moment not found"}` |
| Moment not found (CMS) | 404 | `{"detail": "Moment not found"}` |
| Draft moment accessed publicly | 404 | `{"detail": "Moment not found"}` |
| Invalid title length | 422 | Pydantic validation error |
| Invalid description length | 422 | Pydantic validation error |
| Too many photos (>2) | 422 | Pydantic validation error |
| Missing auth token | 401 | `{"detail": "Not authenticated"}` |
| Invalid/expired token | 401 | `{"detail": "Invalid token"}` |
| Invalid content type on presign | 400 | `{"detail": "Only image/jpeg and image/png content types are accepted."}` |

### S3 Deletion Failures

Following the trips pattern, S3 deletions are best-effort:
- Failures are logged but do not block the HTTP response
- The database record is always removed regardless of S3 outcome
- Orphaned S3 objects can be cleaned up via a future maintenance task if needed

### Frontend Error Handling

- **401 responses**: Clear token from localStorage, redirect to `/cms` login
- **Network errors**: Display "Unable to connect to the server" message
- **404 on detail page**: Next.js `notFound()` renders the default 404 page
- **Validation errors**: Display inline error messages next to form fields

## Testing Strategy

### Unit Tests (pytest)

Example-based tests for specific scenarios:
- Create moment with default draft status
- Publish moment sets published_at timestamp
- 404 for non-existent moment ID
- 404 for draft moment on public endpoint
- 401 for unauthenticated CMS requests
- Empty list returns empty state
- Content type validation on presign (existing endpoint, already tested)

### Property-Based Tests (Hypothesis)

Property-based tests using the **Hypothesis** library for Python, configured with minimum 100 examples per test:

- **Property 1**: Generate random sets of moments with varying dates and creation times, verify ordering invariant
- **Property 2**: Generate moments with 0-2 photos at various positions, verify cover_photo_url matches position 1
- **Property 3**: Generate moments with random valid content, verify detail response completeness and photo ordering
- **Property 4**: Generate strings at boundary lengths (0, 1, 150, 151, 2000, 2001) and random lengths, verify acceptance/rejection
- **Property 5**: Generate moments with 1-2 photos, simulate removal, verify position re-sequencing
- **Property 6**: Generate moments with 0-2 photos, delete them, verify all records and S3 calls are cleaned up

Each property test will be tagged with:
```python
# Feature: emis-big-moments, Property {N}: {property_text}
```

### Integration Tests

- End-to-end CMS workflow: create → edit → publish → verify public visibility → delete
- Photo upload flow: presign → upload to S3 → attach to moment → verify CDN URL
- Revalidation: publish moment, verify public page updates within 60 seconds

### Frontend Tests

- Component rendering tests for MomentForm validation behavior
- Page-level tests for empty states and error states
- Accessibility: form labels, alt text on images, semantic HTML
