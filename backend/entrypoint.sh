#!/bin/sh
set -e

# Ensure Alembic knows the current state of the database before running migrations.
# This handles the case where tables were created by create_all() without Alembic tracking.
python -c "
from app.database import engine
from sqlalchemy import inspect, text

insp = inspect(engine)
tables = insp.get_table_names()

# If the DB has our app tables but Alembic thinks it needs to start from scratch,
# we need to stamp it at the right revision.
if 'labels' in tables:
    # Check current alembic version
    current_rev = None
    if 'alembic_version' in tables:
        with engine.connect() as conn:
            result = conn.execute(text('SELECT version_num FROM alembic_version'))
            row = result.fetchone()
            current_rev = row[0] if row else None

    if current_rev is None:
        # Alembic has no record — stamp at the right point
        cols = [c['name'] for c in insp.get_columns('trip_photos')] if 'trip_photos' in tables else []
        if 'media_type' in cols:
            stamp_rev = 'e5f7a3c82d91'
        else:
            stamp_rev = 'd8a4e2b19c73'
        import subprocess
        subprocess.run(['alembic', 'stamp', stamp_rev], check=True)
        print(f'Stamped alembic_version at {stamp_rev}')
    else:
        print(f'Alembic already at revision: {current_rev}')
else:
    print('Fresh database — alembic upgrade will create all tables')
"

# Now run any pending migrations
alembic upgrade head

# Start the app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
