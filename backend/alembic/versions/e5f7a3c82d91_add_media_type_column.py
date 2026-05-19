"""add_media_type_column

Revision ID: e5f7a3c82d91
Revises: d8a4e2b19c73
Create Date: 2026-06-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f7a3c82d91'
down_revision: Union[str, Sequence[str], None] = 'd8a4e2b19c73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('moment_photos', sa.Column('media_type', sa.String(10), nullable=False, server_default='photo'))
    op.add_column('trip_photos', sa.Column('media_type', sa.String(10), nullable=False, server_default='photo'))
    op.add_column('art_pieces', sa.Column('media_type', sa.String(10), nullable=False, server_default='photo'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('moment_photos', 'media_type')
    op.drop_column('trip_photos', 'media_type')
    op.drop_column('art_pieces', 'media_type')
