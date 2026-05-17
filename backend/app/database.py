import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Load .env file if present (for local development)
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# Production path is /data/emisofia.db inside the Docker container.
# Override via DATABASE_URL env var for local dev and tests.
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:////data/emisofia.db"
)

# Ensure the database directory exists (handles first boot before volume is attached)
_db_url = SQLALCHEMY_DATABASE_URL
if _db_url.startswith("sqlite:///"):
    _db_path = _db_url.replace("sqlite:///", "", 1)
    # Absolute paths start with / after stripping sqlite:///
    # Relative paths (like ./emisofia.db) work as-is
    _db_dir = os.path.dirname(os.path.abspath(_db_path))
    os.makedirs(_db_dir, exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, connection_record):
    """Enable WAL mode for better concurrent read performance."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
