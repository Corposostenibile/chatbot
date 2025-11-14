"""add ai_models table

Revision ID: f004716a5d6b
Revises: 1d3eb860c333
Create Date: 2025-11-14 12:21:51.456974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f004716a5d6b'
down_revision: Union[str, Sequence[str], None] = '1d3eb860c333'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
