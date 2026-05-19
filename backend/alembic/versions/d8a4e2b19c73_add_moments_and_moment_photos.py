"""add_moments_and_moment_photos

Revision ID: d8a4e2b19c73
Revises: c7e9f1a23b56
Create Date: 2026-06-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a4e2b19c73'
down_revision: Union[str, Sequence[str], None] = 'c7e9f1a23b56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('moments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('moment_date', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('moment_photos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('moment_id', sa.Integer(), nullable=False),
        sa.Column('s3_key', sa.String(length=512), nullable=False),
        sa.Column('cdn_url', sa.String(length=1024), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['moment_id'], ['moments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_moment_photos_moment_id', 'moment_photos', ['moment_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_moment_photos_moment_id', table_name='moment_photos')
    op.drop_table('moment_photos')
    op.drop_table('moments')
