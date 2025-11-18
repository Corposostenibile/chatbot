"""Add completed flag to human_tasks

Revision ID: c2e4f7b2b3d4
Revises: ae3d7b8f9c1
Create Date: 2025-11-18 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c2e4f7b2b3d4'
down_revision = 'ae3d7b8f9c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('human_tasks', sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    # remove server_default for portability (set default at model level)
    op.alter_column('human_tasks', 'completed', server_default=None)


def downgrade() -> None:
    op.drop_column('human_tasks', 'completed')
