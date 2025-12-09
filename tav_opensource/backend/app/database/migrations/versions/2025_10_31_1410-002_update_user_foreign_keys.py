"""Update foreign keys to match new user table structure

Revision ID: 002_update_user_fks
Revises: 001_user_restructure
Create Date: 2025-10-31 14:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_update_user_fks'
down_revision: Union[str, None] = '001_user_restructure'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Update foreign key columns in related tables to match new user.id type.
    
    Changes all user_id foreign key columns from String(36) to BigInteger
    to match the new users table structure.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Update audit_logs table
    if 'audit_logs' in tables:
        with op.batch_alter_table('audit_logs', schema=None) as batch_op:
            # Drop and recreate the column with new type
            batch_op.drop_column('user_id')
            batch_op.add_column(sa.Column('user_id', sa.BigInteger(), nullable=True))
            batch_op.create_foreign_key('fk_audit_logs_user_id', 'users', ['user_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index('idx_audit_logs_user_id', ['user_id'], unique=False)
    
    # Update api_keys table
    if 'api_keys' in tables:
        with op.batch_alter_table('api_keys', schema=None) as batch_op:
            batch_op.drop_column('user_id')
            batch_op.add_column(sa.Column('user_id', sa.BigInteger(), nullable=False))
            batch_op.create_foreign_key('fk_api_keys_user_id', 'users', ['user_id'], ['id'], ondelete='CASCADE')
            batch_op.create_index('idx_api_keys_user_id', ['user_id'], unique=False)
    
    # Update workflows table
    if 'workflows' in tables:
        with op.batch_alter_table('workflows', schema=None) as batch_op:
            batch_op.drop_column('author_id')
            batch_op.add_column(sa.Column('author_id', sa.BigInteger(), nullable=True))
            batch_op.create_foreign_key('fk_workflows_author_id', 'users', ['author_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index('idx_workflows_author_id', ['author_id'], unique=False)
    
    # Update files table
    if 'files' in tables:
        with op.batch_alter_table('files', schema=None) as batch_op:
            batch_op.drop_column('uploaded_by_id')
            batch_op.add_column(sa.Column('uploaded_by_id', sa.BigInteger(), nullable=True))
            batch_op.create_foreign_key('fk_files_uploaded_by_id', 'users', ['uploaded_by_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index('idx_files_uploaded_by_id', ['uploaded_by_id'], unique=False)
    
    # Update executions table
    if 'executions' in tables:
        with op.batch_alter_table('executions', schema=None) as batch_op:
            batch_op.drop_column('started_by_id')
            batch_op.add_column(sa.Column('started_by_id', sa.BigInteger(), nullable=True))
            batch_op.create_foreign_key('fk_executions_started_by_id', 'users', ['started_by_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index('idx_executions_started_by_id', ['started_by_id'], unique=False)


def downgrade() -> None:
    """
    Revert foreign key columns back to String(36) type.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Revert audit_logs table
    if 'audit_logs' in tables:
        with op.batch_alter_table('audit_logs', schema=None) as batch_op:
            batch_op.drop_index('idx_audit_logs_user_id')
            batch_op.drop_constraint('fk_audit_logs_user_id', type_='foreignkey')
            batch_op.drop_column('user_id')
            batch_op.add_column(sa.Column('user_id', sa.String(36), nullable=True))
            batch_op.create_foreign_key('fk_audit_logs_user_id', 'users', ['user_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index('idx_audit_logs_user_id', ['user_id'], unique=False)
    
    # Revert api_keys table
    if 'api_keys' in tables:
        with op.batch_alter_table('api_keys', schema=None) as batch_op:
            batch_op.drop_index('idx_api_keys_user_id')
            batch_op.drop_constraint('fk_api_keys_user_id', type_='foreignkey')
            batch_op.drop_column('user_id')
            batch_op.add_column(sa.Column('user_id', sa.String(36), nullable=False))
            batch_op.create_foreign_key('fk_api_keys_user_id', 'users', ['user_id'], ['id'], ondelete='CASCADE')
            batch_op.create_index('idx_api_keys_user_id', ['user_id'], unique=False)
    
    # Revert workflows table
    if 'workflows' in tables:
        with op.batch_alter_table('workflows', schema=None) as batch_op:
            batch_op.drop_index('idx_workflows_author_id')
            batch_op.drop_constraint('fk_workflows_author_id', type_='foreignkey')
            batch_op.drop_column('author_id')
            batch_op.add_column(sa.Column('author_id', sa.String(36), nullable=True))
            batch_op.create_foreign_key('fk_workflows_author_id', 'users', ['author_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index('idx_workflows_author_id', ['author_id'], unique=False)
    
    # Revert files table
    if 'files' in tables:
        with op.batch_alter_table('files', schema=None) as batch_op:
            batch_op.drop_index('idx_files_uploaded_by_id')
            batch_op.drop_constraint('fk_files_uploaded_by_id', type_='foreignkey')
            batch_op.drop_column('uploaded_by_id')
            batch_op.add_column(sa.Column('uploaded_by_id', sa.String(36), nullable=True))
            batch_op.create_foreign_key('fk_files_uploaded_by_id', 'users', ['uploaded_by_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index('idx_files_uploaded_by_id', ['uploaded_by_id'], unique=False)
    
    # Revert executions table
    if 'executions' in tables:
        with op.batch_alter_table('executions', schema=None) as batch_op:
            batch_op.drop_index('idx_executions_started_by_id')
            batch_op.drop_constraint('fk_executions_started_by_id', type_='foreignkey')
            batch_op.drop_column('started_by_id')
            batch_op.add_column(sa.Column('started_by_id', sa.String(36), nullable=True))
            batch_op.create_foreign_key('fk_executions_started_by_id', 'users', ['started_by_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index('idx_executions_started_by_id', ['started_by_id'], unique=False)

