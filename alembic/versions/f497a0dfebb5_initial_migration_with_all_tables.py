"""Initial migration with all tables - sessions, messages, system_prompts

Revision ID: f497a0dfebb5
Revises:
Create Date: 2025-11-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg


# revision identifiers, used by Alembic.
revision: str = 'f497a0dfebb5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create sessions table
    # Ensure enum exists before creating the table; avoid race conditions when
    # applying multiple heads in parallel or in different branches.
    # Using a DO block to create the enum only if not exists prevents
    # psycopg2.errors.DuplicateObject when migrations run concurrently.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'lifecyclestage') THEN
                CREATE TYPE lifecyclestage AS ENUM ('NUOVA_LEAD', 'CONTRASSEGNATO', 'IN_TARGET', 'LINK_DA_INVIARE', 'LINK_INVIATO');
            END IF;
        END
        $$;
        """
    )

    op.create_table('sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        # Prevent SQLAlchemy from trying to create the enum type again by
        # using the dialect-specific ENUM with create_type=False.
        sa.Column('current_lifecycle', pg.ENUM('NUOVA_LEAD', 'CONTRASSEGNATO', 'IN_TARGET', 'LINK_DA_INVIARE', 'LINK_INVIATO', name='lifecyclestage', create_type=False), nullable=False),
        sa.Column('user_info', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'], unique=False)
    op.create_index(op.f('ix_sessions_session_id'), 'sessions', ['session_id'], unique=False)

    # Create messages table
    op.create_table('messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
    op.create_index(op.f('ix_messages_session_id'), 'messages', ['session_id'], unique=False)

    # Create system_prompts table
    op.create_table('system_prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_system_prompts_id'), 'system_prompts', ['id'], unique=False)
    op.create_index(op.f('ix_system_prompts_name'), 'system_prompts', ['name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_system_prompts_name'), table_name='system_prompts')
    op.drop_index(op.f('ix_system_prompts_id'), table_name='system_prompts')
    op.drop_table('system_prompts')
    op.drop_index(op.f('ix_messages_session_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_sessions_session_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_id'), table_name='sessions')
    op.drop_table('sessions')
    # Drop the enum type
    op.execute('DROP TYPE IF EXISTS lifecyclestage')