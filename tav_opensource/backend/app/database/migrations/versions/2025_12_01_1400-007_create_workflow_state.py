"""Create workflow_state table

Revision ID: 007_workflow_state
Revises: 2025_11_27_0001
Create Date: 2025-12-01

Adds workflow_state table for persistent state management across workflow executions.
This enables workflows to maintain state between runs (inventory, checkpoints, etc.)
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '007_workflow_state'
down_revision = '2025_11_27_0001'
branch_labels = None
depends_on = None


def upgrade():
    """Create workflow_state table"""
    op.create_table(
        'workflow_state',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False, comment='Primary key (UUID)'),
        sa.Column('workflow_id', sa.String(36), nullable=False, comment='Workflow this state belongs to'),
        sa.Column('state_key', sa.String(255), nullable=False, comment='State identifier (e.g., "inventory", "checkpoint")'),
        sa.Column('state_namespace', sa.String(100), nullable=True, comment='Optional namespace (e.g., "production", "simulation")'),
        sa.Column('state_value', sa.JSON, nullable=False, comment='State data (flexible JSON)'),
        sa.Column('state_version', sa.Integer, nullable=False, default=1, comment='State version number'),
        sa.Column('last_updated_by_execution', sa.String(36), nullable=True, comment='Execution that last updated this state'),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=False, comment='Last update timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Creation timestamp'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Optional expiration for auto-cleanup'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workflow_id', 'state_key', 'state_namespace', name='uq_workflow_state_key_namespace'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_updated_by_execution'], ['executions.id'], ondelete='SET NULL'),
    )
    
    # Create indexes
    op.create_index('idx_workflow_state_workflow', 'workflow_state', ['workflow_id', 'state_namespace'])
    op.create_index('idx_workflow_state_key', 'workflow_state', ['state_key'])
    op.create_index('idx_workflow_state_expires', 'workflow_state', ['expires_at'])


def downgrade():
    """Drop workflow_state table"""
    op.drop_index('idx_workflow_state_expires', table_name='workflow_state')
    op.drop_index('idx_workflow_state_key', table_name='workflow_state')
    op.drop_index('idx_workflow_state_workflow', table_name='workflow_state')
    op.drop_table('workflow_state')

