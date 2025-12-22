"""Add file_type and file_category columns

Revision ID: add_file_columns
Revises: 
Create Date: 2024-11-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_file_columns'
down_revision = '002_update_user_fks'  # Fixed: was None
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    # Only run if files table exists
    if 'files' not in tables:
        print("Files table doesn't exist yet, skipping add_file_columns migration")
        return
    
    # Check existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('files')]
    
    # Add file_type column if it doesn't exist
    if 'file_type' not in existing_columns:
        op.add_column('files', sa.Column('file_type', sa.String(20), nullable=True))
        op.execute("UPDATE files SET file_type = 'upload' WHERE file_type IS NULL")
        op.alter_column('files', 'file_type', nullable=False)
        op.create_index('idx_files_file_type', 'files', ['file_type'])
    
    # Add file_category column if it doesn't exist
    if 'file_category' not in existing_columns:
        op.add_column('files', sa.Column('file_category', sa.String(20), nullable=True))
        op.execute("UPDATE files SET file_category = 'other' WHERE file_category IS NULL")
        op.alter_column('files', 'file_category', nullable=False)
        op.create_index('idx_files_file_category', 'files', ['file_category'])
    
    # Add workflow_id column if it doesn't exist
    if 'workflow_id' not in existing_columns:
        op.add_column('files', sa.Column('workflow_id', sa.String(36), nullable=True))
        op.create_index('idx_files_workflow_id', 'files', ['workflow_id'])
    
    # Add execution_id column if it doesn't exist
    if 'execution_id' not in existing_columns:
        op.add_column('files', sa.Column('execution_id', sa.String(36), nullable=True))


def downgrade():
    op.drop_index('idx_files_workflow_id', 'files')
    op.drop_index('idx_files_file_category', 'files')
    op.drop_index('idx_files_file_type', 'files')
    op.drop_column('files', 'execution_id')
    op.drop_column('files', 'workflow_id')
    op.drop_column('files', 'file_category')
    op.drop_column('files', 'file_type')

