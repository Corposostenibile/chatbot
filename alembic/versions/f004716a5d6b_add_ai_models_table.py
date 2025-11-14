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
    op.create_table(
        'ai_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_ai_models_name'), 'ai_models', ['name'], unique=True)
    
    # Insert default models
    op.execute("""
        INSERT INTO ai_models (name, display_name, is_active, description, created_at, updated_at)
        VALUES
            ('gemini-flash-latest', 'Gemini Flash Latest', TRUE, 'Fast model optimized for latency', NOW(), NOW()),
            ('gemini-2.5-pro', 'Gemini 2.5 Pro', FALSE, 'Advanced model with extended capabilities', NOW(), NOW())
        ON CONFLICT (name) DO NOTHING
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ai_models_name'), table_name='ai_models')
    op.drop_table('ai_models')
