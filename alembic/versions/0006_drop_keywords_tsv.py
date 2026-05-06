"""drop_keywords_tsv

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-05-06 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('idx_knowledge_chunks_keywords_tsv', table_name='knowledge_chunks')
    op.drop_column('knowledge_chunks', 'keywords_tsv')


def downgrade() -> None:
    op.add_column('knowledge_chunks', sa.Column('keywords_tsv', TSVECTOR(), nullable=True))
    op.create_index(
        'idx_knowledge_chunks_keywords_tsv',
        'knowledge_chunks',
        ['keywords_tsv'],
        postgresql_using='gin',
    )
