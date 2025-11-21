"""merge_heads

Revision ID: 7276091df076
Revises: 10c3d8a7f8b1, baddb34d, merge_f004_ae3d7b8f9c1
Create Date: 2025-11-21 15:02:15.115215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7276091df076'
down_revision: Union[str, Sequence[str], None] = ('10c3d8a7f8b1', 'baddb34d', 'merge_f004_ae3d7b8f9c1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
