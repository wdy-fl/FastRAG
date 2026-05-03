"""add chunk_count to ingestion_tasks

Revision ID: a1b2c3d4e5f6
Revises: e27c6d7b8296
Create Date: 2026-05-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e27c6d7b8296'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ingestion_tasks',
        sa.Column('chunk_count', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('ingestion_tasks', 'chunk_count')
