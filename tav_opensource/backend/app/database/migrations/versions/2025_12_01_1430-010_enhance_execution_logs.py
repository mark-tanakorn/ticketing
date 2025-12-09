"""Enhance execution_logs for event tracking

Revision ID: 010_enhance_execution_logs
Revises: 009_enhance_execution_results
Create Date: 2025-12-01

Adds event and anomaly tracking capabilities to execution_logs.
Enables performance monitoring, failure classification, and issue resolution tracking.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010_enhance_execution_logs'
down_revision = '009_enhance_execution_results'
branch_labels = None
depends_on = None


def upgrade():
    """Add event/anomaly tracking columns to execution_logs"""
    
    # Add event-specific columns
    with op.batch_alter_table('execution_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('event_type', sa.String(100), nullable=True, comment='Event classification (anomaly, failure, alert, milestone)'))
        batch_op.add_column(sa.Column('event_category', sa.String(100), nullable=True, comment='Event category (performance, data_quality, business_logic)'))
        batch_op.add_column(sa.Column('severity', sa.String(20), nullable=True, comment='Severity level (low, medium, high, critical)'))
        batch_op.add_column(sa.Column('impact_score', sa.Float, nullable=True, comment='Impact score (0-10)'))
        batch_op.add_column(sa.Column('affected_metrics', sa.JSON, nullable=True, comment='Metrics affected by this event'))
        batch_op.add_column(sa.Column('resolved', sa.Boolean, nullable=False, server_default='0', comment='Whether issue is resolved'))
        batch_op.add_column(sa.Column('resolution_notes', sa.Text, nullable=True, comment='Resolution details'))
        batch_op.add_column(sa.Column('detection_method', sa.String(100), nullable=True, comment='How was this detected (rule, ml, threshold)'))
        batch_op.add_column(sa.Column('iteration_number', sa.Integer, nullable=True, comment='Iteration number (for loop-based workflows)'))
        
        # Add indexes
        batch_op.create_index('idx_exec_logs_event_type', ['event_type'])
        batch_op.create_index('idx_exec_logs_event_category', ['event_category'])
        batch_op.create_index('idx_exec_logs_severity', ['severity'])
        batch_op.create_index('idx_exec_logs_unresolved', ['resolved', 'severity'])


def downgrade():
    """Remove event tracking columns"""
    
    # Remove columns
    with op.batch_alter_table('execution_logs', schema=None) as batch_op:
        batch_op.drop_index('idx_exec_logs_unresolved')
        batch_op.drop_index('idx_exec_logs_severity')
        batch_op.drop_index('idx_exec_logs_event_category')
        batch_op.drop_index('idx_exec_logs_event_type')
        batch_op.drop_column('iteration_number')
        batch_op.drop_column('detection_method')
        batch_op.drop_column('resolution_notes')
        batch_op.drop_column('resolved')
        batch_op.drop_column('affected_metrics')
        batch_op.drop_column('impact_score')
        batch_op.drop_column('severity')
        batch_op.drop_column('event_category')
        batch_op.drop_column('event_type')

