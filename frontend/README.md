# Notes for Emi — Frontend

Next.js application serving both the public website and the CMS admin interface.

## Prerequisites

- Node.js 18+ (tested with Node 24)
- npm
- The backend API running locally (see `backend/README.md`)

## Quick Start

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure environment variables

Create a `.env.local` file (or `.env`) in the `frontend/` directory:

```dotenv
# Backend API URL (the FastAPI server)
NEXT_PUBLIC_API_URL=http://localhost:8000

# Secret for ISR revalidation (must match between frontend and CMS calls)
NEXT_PUBLIC_REVALIDATE_SECRET=dev-secret
REVALIDATE_SECRET=dev-secret
```

**Important:** Do NOT wrap values in quotes.

### 3. Start the development server

```bash
npm run dev
```

The frontend is now running at `http://localhost:3000`.

Make sure the backend is also running at `http://localhost:8000` (see `backend/README.md`).

## Pages

### Public (no auth required)

| URL | Description |
|-----|-------------|
| http://localhost:3000/notes | Note list — all published notes |
| http://localhost:3000/notes/{id} | Note detail — full note with photos and labels |

### CMS (password required)

| URL | Description |
|-----|-------------|
| http://localhost:3000/cms | Login page |
| http://localhost:3000/cms/notes | Note management — list all notes (drafts + published) |
| http://localhost:3000/cms/notes/new | Create a new note |
| http://localhost:3000/cms/notes/{id}/edit | Edit an existing note |

## Local Development vs Production

### Database

Local dev uses a separate SQLite file (`backend/emisofia.db`) — completely isolated from production. No risk of data leaking between environments.

### Photo Uploads (S3)

To prevent local testing from uploading photos to your production S3 bucket, use one of these approaches:

**Option A: Separate dev bucket (recommended)**

Create a second S3 bucket (e.g., `emisofia-photos-dev`) and point your local `backend/.env` to it:

```dotenv
S3_BUCKET=emisofia-photos-dev
CLOUDFRONT_DOMAIN=your-dev-cloudfront-domain.cloudfront.net
```

**Option B: Skip photo uploads locally**

Leave `S3_BUCKET` empty in your local `backend/.env`. The photo upload will fail gracefully, but all other features (note CRUD, labels, rich text editing) work fine without it.

**Option C: Use LocalStack**

Run a local S3-compatible service:

```bash
docker run -p 4566:4566 localstack/localstack
```

Then configure your backend `.env`:

```dotenv
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
S3_BUCKET=emisofia-photos-dev
```

(Requires modifying the presign endpoint to use a custom S3 endpoint URL.)

### Summary of environment isolation

| Concern | Local Dev | Production |
|---------|-----------|------------|
| Database | `backend/emisofia.db` (local file) | `/data/emisofia.db` (Coolify volume) |
| S3 Bucket | `emisofia-photos-dev` (or empty) | `emisofia-photos` |
| CloudFront | Dev distribution (or skip) | Production distribution |
| Domain | `localhost:3000` | `emisofia.com` |

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout with nav
│   ├── globals.css             # Tailwind + note-photo float styles
│   ├── notes/
│   │   ├── page.tsx            # Public note list (ISR)
│   │   └── [id]/
│   │       └── page.tsx        # Public note detail (ISR)
│   ├── cms/
│   │   ├── page.tsx            # CMS login
│   │   ├── layout.tsx          # CMS auth guard + header
│   │   └── notes/
│   │       ├── page.tsx        # CMS note list
│   │       ├── new/
│   │       │   └── page.tsx    # New note form
│   │       └── [id]/
│   │           └── edit/
│   │               └── page.tsx # Edit note form
│   └── api/
│       └── revalidate/
│           └── route.ts        # ISR revalidation endpoint
├── components/
│   ├── NoteEditor.tsx          # Tiptap rich-text editor
│   ├── PhotoUpload.tsx         # Photo upload with S3 presign
│   ├── LabelInput.tsx          # Label/tag input with validation
│   └── LabelInput.test.tsx     # Unit tests for LabelInput
├── next.config.mjs             # Next.js config (standalone output)
├── tailwind.config.ts          # Tailwind configuration
├── vitest.config.ts            # Vitest test configuration
├── package.json
├── Dockerfile                  # Production multi-stage build
└── .env.local                  # Local environment variables (not in git)
```

## Running Tests

```bash
npm test
```

Or in watch mode:

```bash
npm run test:watch
```

## Building for Production

```bash
npm run build
```

This produces a standalone output in `.next/standalone/` that can be run with `node server.js`.

## Docker Build

```bash
docker build -t emisofia-frontend .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  -e REVALIDATE_SECRET=your-secret \
  emisofia-frontend
```

## Troubleshooting

### "Configuring Next.js via 'next.config.ts' is not supported"

The config file should be `next.config.mjs` (not `.ts`). If you see a `next.config.ts` file, delete it — `next.config.mjs` is the correct one.

### Photos not loading in note detail

Photos are embedded in the `body_html` as `<img>` tags pointing to CloudFront URLs. If you're testing locally without a real CloudFront distribution, the images will show as broken. This is expected — the text content and layout still work correctly.

### "Could not validate credentials" when using the CMS

Make sure you're logged in at `/cms` first. The JWT is stored in `localStorage`. If it expires (after 24 hours), just log in again.

### CORS errors in the browser console

Make sure the backend has CORS configured to allow `http://localhost:3000`. Check `CORS_ORIGINS` in `backend/.env` — it defaults to `*` which allows everything in dev.
