"""Add is_batch_waiting and batch_started_at to sessions

Revision ID: baddb34d
Revises: ae3d7b8f9c1
Create Date: 2025-11-17 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'baddb34d'
down_revision: Union[str, Sequence[str], None] = 'ae3d7b8f9c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('is_batch_waiting', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('sessions', sa.Column('batch_started_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'batch_started_at')
    op.drop_column('sessions', 'is_batch_waiting')
