"""Add email_interactions table

Revision ID: 004_email_interactions
Revises: 003_unified_status
Create Date: 2025-11-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '004_email_interactions'
down_revision = ('003_unified_status', 'add_file_columns')  # Merge both heads
branch_labels = None
depends_on = None


def upgrade():
    """Create email_interactions table"""
    op.create_table(
        'email_interactions',
        sa.Column('id', sa.String(), nullable=False, comment='interaction_id (UUID)'),
        sa.Column('token', sa.String(), nullable=False, comment='Secure verification token'),
        sa.Column('execution_id', sa.String(length=36), nullable=False, comment='Execution this interaction belongs to'),
        sa.Column('workflow_id', sa.String(length=36), nullable=False, comment='Workflow this interaction belongs to'),
        sa.Column('node_id', sa.String(), nullable=False, comment='Approval node that created this interaction'),
        
        sa.Column('original_draft', sa.JSON(), nullable=False, comment='Original email draft from composer'),
        sa.Column('edited_draft', sa.JSON(), nullable=True, comment='User-edited draft after review'),
        sa.Column('smtp_config', sa.JSON(), nullable=False, comment='SMTP configuration for sending'),
        
        sa.Column('status', sa.String(), nullable=False, comment='pending, approved, rejected, expired, sent'),
        sa.Column('action', sa.String(), nullable=True, comment='approve, reject'),
        
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='When interaction was created'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, comment='When interaction expires'),
        sa.Column('submitted_at', sa.DateTime(), nullable=True, comment='When user submitted decision'),
        sa.Column('sent_at', sa.DateTime(), nullable=True, comment='When email was sent'),
        
        sa.Column('user_agent', sa.String(), nullable=True, comment='Browser user agent'),
        sa.Column('ip_address', sa.String(), nullable=True, comment='IP address of submission'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_email_interaction_token', 'email_interactions', ['token'], unique=True)
    op.create_index('idx_email_interaction_execution', 'email_interactions', ['execution_id'])
    op.create_index('idx_email_interaction_workflow', 'email_interactions', ['workflow_id'])
    op.create_index('idx_email_interaction_status', 'email_interactions', ['status'])
    op.create_index('idx_email_interaction_expires', 'email_interactions', ['expires_at'])
    op.create_index('idx_email_interaction_status_expires', 'email_interactions', ['status', 'expires_at'])


def downgrade():
    """Drop email_interactions table"""
    op.drop_index('idx_email_interaction_status_expires', table_name='email_interactions')
    op.drop_index('idx_email_interaction_expires', table_name='email_interactions')
    op.drop_index('idx_email_interaction_status', table_name='email_interactions')
    op.drop_index('idx_email_interaction_workflow', table_name='email_interactions')
    op.drop_index('idx_email_interaction_execution', table_name='email_interactions')
    op.drop_index('idx_email_interaction_token', table_name='email_interactions')
    op.drop_table('email_interactions')

