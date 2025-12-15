"""Enhance workflows for templates

Revision ID: 011_enhance_workflows_templates
Revises: 010_enhance_execution_logs
Create Date: 2025-12-01

Adds template management capabilities to workflows table.
Enables template categorization, usage tracking, and inheritance.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011_enhance_workflows_templates'
down_revision = '010_enhance_execution_logs'
branch_labels = None
depends_on = None


def upgrade():
    """Add template management columns to workflows"""
    
    # Add template-specific columns
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.add_column(sa.Column('template_category', sa.String(100), nullable=True, comment='Template category (for is_template=true)'))
        batch_op.add_column(sa.Column('template_subcategory', sa.String(100), nullable=True, comment='Template subcategory'))
        batch_op.add_column(sa.Column('template_usage_count', sa.Integer, nullable=False, server_default='0', comment='Number of times template used'))
        batch_op.add_column(sa.Column('template_rating', sa.Float, nullable=True, comment='Average user rating'))
        batch_op.add_column(sa.Column('template_validation_schema', sa.JSON, nullable=True, comment='Validation rules for template'))
        batch_op.add_column(sa.Column('template_instructions', sa.Text, nullable=True, comment='Setup instructions for template'))
        batch_op.add_column(sa.Column('parent_template_id', sa.String(36), nullable=True, comment='Parent template ID (for derived templates)'))
        
        # Add indexes
        batch_op.create_index('idx_workflows_template_category', ['template_category'])
        batch_op.create_index('idx_workflows_is_template_category', ['is_template', 'template_category'])


def downgrade():
    """Remove template management columns"""
    
    # Remove columns
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.drop_index('idx_workflows_is_template_category')
        batch_op.drop_index('idx_workflows_template_category')
        batch_op.drop_column('parent_template_id')
        batch_op.drop_column('template_instructions')
        batch_op.drop_column('template_validation_schema')
        batch_op.drop_column('template_rating')
        batch_op.drop_column('template_usage_count')
        batch_op.drop_column('template_subcategory')
        batch_op.drop_column('template_category')

