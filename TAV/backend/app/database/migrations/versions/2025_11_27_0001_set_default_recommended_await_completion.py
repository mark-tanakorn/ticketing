"""set_default_recommended_await_completion

Revision ID: 2025_11_27_0001
Revises: 2025_11_18_0000-006
Create Date: 2025-11-27

Sets the default value for recommended_await_completion to 'false' for existing workflows
and updates the column to be non-nullable with a default value.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_11_27_0001'
down_revision = '006_recommended_await'  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Update existing workflows to have 'false' as the default value for recommended_await_completion
    and make the column non-nullable with a default.
    
    SQLite doesn't support ALTER COLUMN for constraints, so we need to use batch_alter_table.
    """
    # First, update all NULL values to 'false'
    op.execute("""
        UPDATE workflows 
        SET recommended_await_completion = 'false' 
        WHERE recommended_await_completion IS NULL
    """)
    
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.alter_column(
            'recommended_await_completion',
            existing_type=sa.String(50),
            nullable=False,
            server_default='false'
        )


def downgrade():
    """
    Revert the column to nullable without a default.
    
    SQLite doesn't support ALTER COLUMN for constraints, so we need to use batch_alter_table.
    """
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.alter_column(
            'recommended_await_completion',
            existing_type=sa.String(50),
            nullable=True,
            server_default=None
        )

