"""intent_node_kb_link

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-05 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'intent_nodes',
        sa.Column('knowledge_base_id', sa.String(length=36), nullable=True)
    )
    op.create_foreign_key(
        'fk_intent_nodes_knowledge_base_id',
        'intent_nodes', 'knowledge_bases',
        ['knowledge_base_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_intent_nodes_knowledge_base_id', 'intent_nodes', type_='foreignkey')
    op.drop_column('intent_nodes', 'knowledge_base_id')
