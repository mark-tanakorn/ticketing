"""Enhance execution_results for artifacts

Revision ID: 009_enhance_execution_results
Revises: 008_execution_iterations
Create Date: 2025-12-01

Adds artifact management capabilities to execution_results table.
Enables versioning, tagging, and tracking artifact usage across executions.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_enhance_execution_results'
down_revision = '008_execution_iterations'
branch_labels = None
depends_on = None


def upgrade():
    """Add artifact management columns to execution_results"""
    
    # Add artifact-specific columns
    with op.batch_alter_table('execution_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('artifact_key', sa.String(255), nullable=True, comment='Artifact identifier'))
        batch_op.add_column(sa.Column('artifact_category', sa.String(100), nullable=True, comment='Artifact category'))
        batch_op.add_column(sa.Column('tags', sa.JSON, nullable=True, comment='Searchable tags'))
        batch_op.add_column(sa.Column('version', sa.Integer, nullable=False, server_default='1', comment='Artifact version'))
        batch_op.add_column(sa.Column('replaces_artifact_id', sa.String(36), nullable=True, comment='Previous version artifact ID'))
        batch_op.add_column(sa.Column('referenced_by_executions', sa.JSON, nullable=True, comment='Executions that used this artifact'))
        batch_op.add_column(sa.Column('access_count', sa.Integer, nullable=False, server_default='0', comment='Number of times accessed'))
        batch_op.add_column(sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True, comment='Last access timestamp'))
        batch_op.add_column(sa.Column('workflow_id', sa.String(36), nullable=True, comment='Workflow that created this artifact'))
        batch_op.add_column(sa.Column('description', sa.Text, nullable=True, comment='Artifact description'))
        
        # Add indexes
        batch_op.create_index('idx_exec_results_artifact_key', ['artifact_key'])
        batch_op.create_index('idx_exec_results_artifact_category', ['artifact_category'])
        batch_op.create_index('idx_exec_results_workflow', ['workflow_id'])


def downgrade():
    """Remove artifact management columns"""
    
    # Remove columns
    with op.batch_alter_table('execution_results', schema=None) as batch_op:
        batch_op.drop_column('description')
        batch_op.drop_column('workflow_id')
        batch_op.drop_column('last_accessed_at')
        batch_op.drop_column('access_count')
        batch_op.drop_column('referenced_by_executions')
        batch_op.drop_column('replaces_artifact_id')
        batch_op.drop_column('version')
        batch_op.drop_column('tags')
        batch_op.drop_column('artifact_category')
        batch_op.drop_column('artifact_key')

