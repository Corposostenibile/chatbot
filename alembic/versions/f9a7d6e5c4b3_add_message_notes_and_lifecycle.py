"""Add lifecycle to messages and message_notes table

Revision ID: f9a7d6e5c4b3
Revises: c2e4f7b2b3d4
Create Date: 2025-11-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = 'f9a7d6e5c4b3'
down_revision: Union[str, Sequence[str], None] = 'c2e4f7b2b3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add lifecycle column to messages using the existing enum type
    op.add_column('messages', sa.Column('lifecycle', pg.ENUM('NUOVA_LEAD', 'CONTRASSEGNATO', 'IN_TARGET', 'LINK_DA_INVIARE', 'LINK_INVIATO', name='lifecyclestage', create_type=False), nullable=True))

    # Create message_notes table to store ratings/comments on messages
    op.create_table(
        'message_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], )
    )
    op.create_index(op.f('ix_message_notes_message_id'), 'message_notes', ['message_id'], unique=False)
    op.create_index(op.f('ix_message_notes_session_id'), 'message_notes', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_message_notes_session_id'), table_name='message_notes')
    op.drop_index(op.f('ix_message_notes_message_id'), table_name='message_notes')
    op.drop_table('message_notes')

    op.drop_column('messages', 'lifecycle')