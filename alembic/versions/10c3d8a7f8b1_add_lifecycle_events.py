"""Add lifecycle_events table

Revision ID: 10c3d8a7f8b1
Revises: f9a7d6e5c4b3
Create Date: 2025-11-19 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = '10c3d8a7f8b1'
down_revision: Union[str, Sequence[str], None] = 'f9a7d6e5c4b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lifecycle_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('previous_lifecycle', pg.ENUM('NUOVA_LEAD', 'CONTRASSEGNATO', 'IN_TARGET', 'LINK_DA_INVIARE', 'LINK_INVIATO', name='lifecyclestage', create_type=False), nullable=True),
        sa.Column('new_lifecycle', pg.ENUM('NUOVA_LEAD', 'CONTRASSEGNATO', 'IN_TARGET', 'LINK_DA_INVIARE', 'LINK_INVIATO', name='lifecyclestage', create_type=False), nullable=False),
        sa.Column('trigger_message_id', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['trigger_message_id'], ['messages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lifecycle_events_session_id'), 'lifecycle_events', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_lifecycle_events_session_id'), table_name='lifecycle_events')
    op.drop_table('lifecycle_events')