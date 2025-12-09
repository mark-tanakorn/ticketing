"""Add credentials table

Revision ID: 005_add_credentials
Revises: 004_email_interactions
Create Date: 2025-11-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '005_add_credentials'
down_revision = '004_email_interactions'
branch_labels = None
depends_on = None


def upgrade():
    """Create credentials table for storing encrypted API keys and OAuth tokens"""
    op.create_table(
        'credentials',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='Primary key'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='User who owns this credential'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='User-friendly name (e.g., "My Slack Workspace")'),
        sa.Column('service_type', sa.String(length=100), nullable=False, comment='Service identifier (e.g., "slack", "google", "github")'),
        sa.Column('auth_type', sa.Enum('API_KEY', 'BEARER_TOKEN', 'BASIC_AUTH', 'OAUTH2', 'SMTP', 'DATABASE', 'CUSTOM', 
                                       name='authtype', create_type=True), nullable=False, comment='Authentication method'),
        sa.Column('encrypted_data', sa.Text(), nullable=False, comment='Encrypted JSON with sensitive credentials'),
        sa.Column('config_metadata', sa.Text(), nullable=True, comment='Non-sensitive JSON metadata (not encrypted)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='Whether credential is active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, comment='Last update timestamp'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True, comment='Last time credential was used'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional description/notes'),
        
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_credentials_user_id', 'credentials', ['user_id'])
    op.create_index('idx_credentials_service_type', 'credentials', ['service_type'])
    op.create_index('idx_credentials_is_active', 'credentials', ['is_active'])
    op.create_index('idx_credentials_user_service', 'credentials', ['user_id', 'service_type'])


def downgrade():
    """Drop credentials table"""
    op.drop_index('idx_credentials_user_service', table_name='credentials')
    op.drop_index('idx_credentials_is_active', table_name='credentials')
    op.drop_index('idx_credentials_service_type', table_name='credentials')
    op.drop_index('idx_credentials_user_id', table_name='credentials')
    op.drop_table('credentials')
    
    # Drop enum type (PostgreSQL only, SQLite doesn't have native enum)
    # This will be skipped automatically for SQLite
    op.execute('DROP TYPE IF EXISTS authtype')

