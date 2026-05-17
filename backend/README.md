# Notes for Emi — Backend

FastAPI REST API for the Notes for Emi website. Handles note CRUD, photo presign URLs, and CMS authentication.

## Prerequisites

- Python 3.12+ (tested with 3.14)
- pip

## Quick Start

### 1. Create a virtual environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS/WSL
# or on Windows CMD: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Configure environment variables

Copy the example file and fill in the values:

```bash
cp ../.env.example .env
```

Edit `backend/.env` with your values:

```dotenv
# Pick any password for local dev, then generate its bcrypt hash (see below)
CMS_PASSWORD_HASH=$2b$12$...your-hash-here...

# Any random string — used to sign JWTs
JWT_SECRET=my-super-secret-dev-key

# SQLite database path for local development
DATABASE_URL=sqlite:///./emisofia.db

# AWS credentials (only needed if testing photo upload)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET=
CLOUDFRONT_DOMAIN=
```

**Important:** Do NOT wrap values in quotes. Write them bare:
```
JWT_SECRET=my-secret-key
```
Not:
```
JWT_SECRET="my-secret-key"   ← wrong, quotes will be included in the value
```

### 4. Generate a CMS password hash

Pick a password for local development and generate its bcrypt hash:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
```

Copy the output (starts with `$2b$12$...`) into `CMS_PASSWORD_HASH` in your `.env` file.

### 5. Run database migrations

```bash
alembic upgrade head
```

This creates `emisofia.db` in the `backend/` directory with all tables.

### 6. Start the development server

```bash
uvicorn app.main:app --reload
```

The API is now running at `http://127.0.0.1:8000`.

## Useful URLs

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/docs | Swagger UI — interactive API explorer |
| http://127.0.0.1:8000/redoc | ReDoc — alternative API docs |
| http://127.0.0.1:8000/health | Health check endpoint |
| http://127.0.0.1:8000/api/notes | Public notes list (no auth needed) |

## Authentication

The CMS uses a single-password JWT flow:

1. **Login:** POST to `/api/cms/auth/login` with `{"password": "yourpassword"}`
2. **Get token:** Response contains `{"access_token": "eyJ...", "token_type": "bearer"}`
3. **Use token:** Include `Authorization: Bearer <token>` header on all `/api/cms/*` endpoints

In Swagger UI (`/docs`), click the **Authorize** button (lock icon) and paste your token to authenticate all CMS requests.

Tokens expire after 24 hours. Simply log in again to get a new one.

## API Endpoints

### Public (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notes` | Paginated list of published notes |
| GET | `/api/notes/{id}` | Single published note detail |

### CMS (Bearer token required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/cms/auth/login` | Exchange password for JWT |
| GET | `/api/cms/notes` | List all notes (drafts + published) |
| POST | `/api/cms/notes` | Create a new note |
| GET | `/api/cms/notes/{id}` | Get a single note (any status) |
| PUT | `/api/cms/notes/{id}` | Update a note |
| DELETE | `/api/cms/notes/{id}` | Delete a note |
| POST | `/api/cms/photos/presign` | Get a presigned S3 upload URL |
| DELETE | `/api/cms/photos/{key}` | Delete a photo from S3 |

## Running Tests

```bash
pytest
```

Tests use an in-memory SQLite database — no `.env` configuration needed.

To run with verbose output:

```bash
pytest -v
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, lifespan, router registration
│   ├── config.py        # Settings (reads .env + environment variables)
│   ├── database.py      # SQLAlchemy engine, session, Base
│   ├── models.py        # ORM models (Note, Label, NoteLabel, Photo)
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # JWT creation/verification, password check
│   ├── utils.py         # Excerpt generation, HTML sanitisation, label normalisation
│   └── routers/
│       ├── __init__.py
│       ├── auth.py      # POST /api/cms/auth/login
│       ├── cms_notes.py # CRUD for /api/cms/notes
│       ├── cms_photos.py# Photo presign + delete
│       └── public.py    # GET /api/notes, GET /api/notes/{id}
├── alembic/
│   ├── env.py           # Migration environment (loads .env)
│   └── versions/        # Migration scripts
├── tests/               # pytest test files
├── pyproject.toml       # Project metadata + dependencies
├── alembic.ini          # Alembic configuration
└── .env                 # Local environment variables (not in git)
```

## Troubleshooting

### "unable to open database file"

Your `DATABASE_URL` is pointing to a path that doesn't exist. Make sure your `.env` has:
```
DATABASE_URL=sqlite:///./emisofia.db
```

### "Invalid salt" on login

Your `CMS_PASSWORD_HASH` value is malformed. Regenerate it:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
```

### "Could not validate credentials" (401) on CMS endpoints

1. Make sure `JWT_SECRET` is set in your `.env` (not empty, no quotes)
2. Log in again after any `.env` changes to get a fresh token
3. Include the header exactly as: `Authorization: Bearer <token>`

### "Command 'uvicorn' not found"

You're not in the virtual environment. Activate it:
```bash
source .venv/bin/activate
```

### setuptools build errors on `pip install -e ".[dev]"`

Make sure `pyproject.toml` has `build-backend = "setuptools.build_meta"` (not `setuptools.backends.legacy`).
