"""Add is_conversation_finished flag to sessions

Revision ID: 1d3eb860c333
Revises: f8d2c1a2b3e4
Create Date: 2025-11-13 09:45:25.132647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1d3eb860c333'
down_revision: Union[str, Sequence[str], None] = 'f8d2c1a2b3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aggiunge il campo is_conversation_finished alla tabella sessions"""
    # Aggiunge il nuovo campo booleano (nullable inizialmente)
    op.add_column('sessions', sa.Column('is_conversation_finished', sa.Boolean(), nullable=True))

    # Aggiorna tutte le righe esistenti impostando il flag a False
    op.execute("UPDATE sessions SET is_conversation_finished = False WHERE is_conversation_finished IS NULL")

    # Rende la colonna NOT NULL
    op.alter_column('sessions', 'is_conversation_finished', nullable=False, existing_type=sa.Boolean())


def downgrade() -> None:
    """Rimuove il campo is_conversation_finished dalla tabella sessions"""
    # Rimuove la colonna aggiunta
    op.drop_column('sessions', 'is_conversation_finished')
