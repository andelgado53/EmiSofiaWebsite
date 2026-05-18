"""add_art_pieces

Revision ID: c7e9f1a23b56
Revises: b3f8a2c71d4e
Create Date: 2026-05-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e9f1a23b56'
down_revision: Union[str, Sequence[str], None] = 'b3f8a2c71d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('art_pieces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('s3_key', sa.String(length=512), nullable=False),
        sa.Column('cdn_url', sa.String(length=1024), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=10), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_art_pieces_year', 'art_pieces', ['year'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_art_pieces_year', table_name='art_pieces')
    op.drop_table('art_pieces')
