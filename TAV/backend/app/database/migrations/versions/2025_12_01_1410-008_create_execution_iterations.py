"""Create execution_iterations table

Revision ID: 008_execution_iterations
Revises: 007_workflow_state
Create Date: 2025-12-01

Adds execution_iterations table for tracking iterations within a single execution.
This enables loop-based workflows (for, while, simulation days, batch processing, etc.)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_execution_iterations'
down_revision = '007_workflow_state'
branch_labels = None
depends_on = None


def upgrade():
    """Create execution_iterations table"""
    op.create_table(
        'execution_iterations',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False, comment='Primary key (UUID)'),
        sa.Column('execution_id', sa.String(36), nullable=False, comment='Parent execution'),
        sa.Column('iteration_number', sa.Integer, nullable=False, comment='Iteration sequence number'),
        sa.Column('iteration_label', sa.String(255), nullable=True, comment='Human-readable label (e.g., "day_5", "batch_42")'),
        
        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, comment='Iteration start time'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='Iteration completion time'),
        sa.Column('duration_ms', sa.Integer, nullable=True, comment='Duration in milliseconds'),
        
        # Virtual vs Real Time (for time-accelerated workflows)
        sa.Column('virtual_timestamp', sa.DateTime(timezone=True), nullable=True, comment='Simulated/virtual time'),
        sa.Column('real_timestamp', sa.DateTime(timezone=True), nullable=False, comment='Actual execution time'),
        sa.Column('time_scale', sa.Float, nullable=False, default=1.0, comment='Time acceleration factor'),
        
        # Iteration Data
        sa.Column('input_data', sa.JSON, nullable=True, comment='Inputs for this iteration'),
        sa.Column('output_data', sa.JSON, nullable=True, comment='Outputs from this iteration'),
        sa.Column('iteration_metadata', sa.JSON, nullable=True, comment='Additional iteration context'),
        
        # Status
        sa.Column('status', sa.String(50), nullable=False, default='running', comment='running, completed, failed, skipped'),
        sa.Column('error_message', sa.Text, nullable=True, comment='Error details if failed'),
        
        # Performance Metrics
        sa.Column('nodes_executed', sa.Integer, nullable=False, default=0, comment='Number of nodes executed'),
        sa.Column('tokens_used', sa.Integer, nullable=True, comment='LLM tokens used (if applicable)'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('idx_exec_iter_execution', 'execution_iterations', ['execution_id', 'iteration_number'])
    op.create_index('idx_exec_iter_status', 'execution_iterations', ['execution_id', 'status'])
    op.create_index('idx_exec_iter_virtual_time', 'execution_iterations', ['execution_id', 'virtual_timestamp'])


def downgrade():
    """Drop execution_iterations table"""
    op.drop_index('idx_exec_iter_virtual_time', table_name='execution_iterations')
    op.drop_index('idx_exec_iter_status', table_name='execution_iterations')
    op.drop_index('idx_exec_iter_execution', table_name='execution_iterations')
    op.drop_table('execution_iterations')

