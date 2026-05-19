#!/bin/sh
set -e

# If the database already has tables but Alembic has never been run
# (no alembic_version table), stamp it at the last pre-video-upload migration
# so that only new migrations are applied.
python -c "
from app.database import engine
from sqlalchemy import inspect

insp = inspect(engine)
tables = insp.get_table_names()

if 'alembic_version' not in tables and 'labels' in tables:
    # DB was created by create_all(), not by Alembic.
    # Check if media_type column already exists (migration already applied manually).
    cols = [c['name'] for c in insp.get_columns('trip_photos')] if 'trip_photos' in tables else []
    if 'media_type' in cols:
        # All migrations are already applied
        stamp_rev = 'e5f7a3c82d91'
    else:
        # Tables exist but media_type migration hasn't run yet
        stamp_rev = 'd8a4e2b19c73'
    import subprocess
    subprocess.run(['alembic', 'stamp', stamp_rev], check=True)
    print(f'Stamped alembic_version at {stamp_rev}')
"

# Now run any pending migrations
alembic upgrade head

# Start the app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
