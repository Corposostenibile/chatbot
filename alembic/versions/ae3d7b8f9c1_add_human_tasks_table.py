"""Add human_tasks table

Revision ID: ae3d7b8f9c1
Revises: f8d2c1a2b3e4_add_default_system_prompt
Create Date: 2025-11-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae3d7b8f9c1'
down_revision: Union[str, Sequence[str], None] = 'f8d2c1a2b3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('human_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='open'),
        sa.Column('assigned_to', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_human_tasks_id'), 'human_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_human_tasks_session_id'), 'human_tasks', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_human_tasks_session_id'), table_name='human_tasks')
    op.drop_index(op.f('ix_human_tasks_id'), table_name='human_tasks')
    op.drop_table('human_tasks')
