"""drop_intent_node_level_and_parent

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-05-05 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('intent_nodes_parent_id_fkey', 'intent_nodes', type_='foreignkey')
    op.drop_column('intent_nodes', 'parent_id')
    op.drop_column('intent_nodes', 'level')


def downgrade() -> None:
    op.add_column('intent_nodes', sa.Column('level', sa.String(length=20), nullable=True))
    op.add_column('intent_nodes', sa.Column('parent_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'intent_nodes_parent_id_fkey',
        'intent_nodes', 'intent_nodes',
        ['parent_id'], ['id'],
    )
