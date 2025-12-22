"""add_recommended_await_completion_to_workflows

Revision ID: 006_recommended_await
Revises: db71871359c0
Create Date: 2025-11-18 00:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_recommended_await'
down_revision = 'db71871359c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add recommended_await_completion column to workflows table.
    
    This field stores a recommendation for API consumers on how to call
    the execute endpoint (e.g., "true", "timeout=30").
    
    This is a hint/indicator only - not enforced. Users can still use any
    X-Await-Completion header value they want regardless of this field.
    """
    op.add_column('workflows', 
        sa.Column('recommended_await_completion', sa.String(50), nullable=True)
    )


def downgrade() -> None:
    """Remove recommended_await_completion column from workflows table."""
    op.drop_column('workflows', 'recommended_await_completion')

