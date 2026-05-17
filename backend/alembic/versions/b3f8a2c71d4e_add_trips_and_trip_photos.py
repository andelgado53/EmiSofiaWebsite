"""add_trips_and_trip_photos

Revision ID: b3f8a2c71d4e
Revises: 0a32561a475e
Create Date: 2026-05-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f8a2c71d4e'
down_revision: Union[str, Sequence[str], None] = '0a32561a475e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('trips',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('trip_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('trip_photos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('s3_key', sa.String(length=512), nullable=False),
        sa.Column('cdn_url', sa.String(length=1024), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trip_photos_trip_id', 'trip_photos', ['trip_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_trip_photos_trip_id', table_name='trip_photos')
    op.drop_table('trip_photos')
    op.drop_table('trips')
