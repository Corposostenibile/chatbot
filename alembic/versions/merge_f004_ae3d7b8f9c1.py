"""Merge revisions f004716a5d6b & ae3d7b8f9c1

Revision ID: merge_f004_ae3d7b8f9c1
Revises: f004716a5d6b, ae3d7b8f9c1
Create Date: 2025-11-17 16:40:00.000000

"""
from alembic import op
# revision identifiers, used by Alembic.
revision = 'merge_f004_ae3d7b8f9c1'
down_revision = ('f004716a5d6b', 'ae3d7b8f9c1')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge migration - no schema changes
    pass


def downgrade() -> None:
    # No-op
    pass
