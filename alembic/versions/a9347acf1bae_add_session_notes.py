"""add_session_notes

Revision ID: a9347acf1bae
Revises: 7276091df076
Create Date: 2025-11-21 15:02:41.674841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a9347acf1bae'
down_revision: Union[str, Sequence[str], None] = '7276091df076'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('session_notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=False),
    sa.Column('created_by', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_session_notes_id'), 'session_notes', ['id'], unique=False)
    op.create_index(op.f('ix_session_notes_session_id'), 'session_notes', ['session_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_session_notes_session_id'), table_name='session_notes')
    op.drop_index(op.f('ix_session_notes_id'), table_name='session_notes')
    op.drop_table('session_notes')
