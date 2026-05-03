"""retrieval_enhancement

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. knowledge_chunks 新增 keywords_tsv 列
    op.add_column(
        'knowledge_chunks',
        sa.Column('keywords_tsv', sa.dialects.postgresql.TSVECTOR(), nullable=True)
    )
    op.create_index(
        'idx_knowledge_chunks_keywords_tsv',
        'knowledge_chunks',
        ['keywords_tsv'],
        postgresql_using='gin',
    )

    # 2. 新增 knowledge_doc_questions 表
    op.create_table(
        'knowledge_doc_questions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('knowledge_base_id', sa.String(length=36), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['knowledge_documents.id']),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_knowledge_doc_questions_embedding',
        'knowledge_doc_questions',
        ['embedding'],
        postgresql_using='ivfflat',
        postgresql_with={'lists': 100},
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )


def downgrade() -> None:
    op.drop_index('idx_knowledge_doc_questions_embedding', table_name='knowledge_doc_questions')
    op.drop_table('knowledge_doc_questions')
    op.drop_index('idx_knowledge_chunks_keywords_tsv', table_name='knowledge_chunks')
    op.drop_column('knowledge_chunks', 'keywords_tsv')
