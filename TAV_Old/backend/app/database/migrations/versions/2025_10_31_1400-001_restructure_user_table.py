"""Restructure user table with comprehensive fields

Revision ID: 001_user_restructure
Revises: 
Create Date: 2025-10-31 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '001_user_restructure'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade the user table structure.
    
    This migration handles the complete restructuring of the users table
    from a simple auth model to a comprehensive employee management model.
    """
    
    # Step 1: Create a backup of existing users table if it exists
    # We need to handle this carefully because we're changing the primary key type
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'users' in inspector.get_table_names():
        # Rename old table to backup
        op.rename_table('users', 'users_backup')
        
        # Create new users table with the new structure
        op.create_table(
            'users',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('agent_id', sa.BigInteger(), nullable=True),
            sa.Column('company_id', sa.BigInteger(), nullable=True),
            sa.Column('user_nric', sa.String(length=50), nullable=True),
            sa.Column('user_name', sa.String(length=255), nullable=False),
            sa.Column('user_initial', sa.String(length=10), nullable=True),
            sa.Column('user_password', sa.String(length=500), nullable=False),
            sa.Column('user_email', sa.String(length=255), nullable=True),
            sa.Column('user_firstname', sa.String(length=255), nullable=True),
            sa.Column('user_lastname', sa.String(length=255), nullable=True),
            sa.Column('user_gender', sa.String(length=20), nullable=True),
            sa.Column('user_maritalstatus', sa.String(length=50), nullable=True),
            sa.Column('user_department_id', sa.BigInteger(), nullable=True),
            sa.Column('user_branch_id', sa.BigInteger(), nullable=True),
            sa.Column('user_officephone', sa.String(length=50), nullable=True),
            sa.Column('user_homephone', sa.String(length=50), nullable=True),
            sa.Column('user_handphone', sa.String(length=50), nullable=True),
            sa.Column('user_address1', sa.String(length=500), nullable=True),
            sa.Column('user_address2', sa.String(length=500), nullable=True),
            sa.Column('user_addresscity', sa.String(length=100), nullable=True),
            sa.Column('user_stateprovince', sa.String(length=100), nullable=True),
            sa.Column('user_postalcode', sa.String(length=20), nullable=True),
            sa.Column('user_citycode', sa.String(length=20), nullable=True),
            sa.Column('user_countrycode', sa.String(length=20), nullable=True),
            sa.Column('user_note', sa.Text(), nullable=True),
            sa.Column('user_is_deleted', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('user_is_disabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_show', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('is_update', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_ad_user', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('user_register_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_created_by', sa.String(length=255), nullable=True),
            sa.Column('user_created_on', sa.DateTime(timezone=True), nullable=False),
            sa.Column('user_modified_by', sa.String(length=255), nullable=True),
            sa.Column('user_modified_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_photo_path', sa.String(length=1000), nullable=True),
            sa.Column('user_signature_path', sa.String(length=1000), nullable=True),
            sa.Column('user_is_firsttime_login', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('user_security_question_id', sa.BigInteger(), nullable=True),
            sa.Column('user_security_answer', sa.String(length=500), nullable=True),
            sa.Column('user_is_trustedhub', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('user_staffcode', sa.String(length=50), nullable=True),
            sa.Column('user_employee_id', sa.String(length=50), nullable=True),
            sa.Column('user_employee_number', sa.String(length=50), nullable=True),
            sa.Column('job_title', sa.String(length=255), nullable=True),
            sa.Column('staff_type', sa.String(length=100), nullable=True),
            sa.Column('highest_education', sa.String(length=255), nullable=True),
            sa.Column('join_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_approval_limit', sa.DECIMAL(18, 2), nullable=True),
            sa.Column('user_deviation_limit', sa.DECIMAL(18, 2), nullable=True),
            sa.Column('supervisor_user_id', sa.Integer(), nullable=True),
            sa.Column('backup_user_id', sa.Integer(), nullable=True),
            sa.Column('user_notification_emails', sa.Text(), nullable=True),
            sa.Column('user_deleted_by', sa.String(length=255), nullable=True),
            sa.Column('user_deleted_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_reset_password_by', sa.String(length=255), nullable=True),
            sa.Column('user_reset_password_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_disabled_by', sa.String(length=255), nullable=True),
            sa.Column('user_disabled_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_enabled_by', sa.String(length=255), nullable=True),
            sa.Column('user_enabled_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_change_password_by', sa.String(length=255), nullable=True),
            sa.Column('user_change_password_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ro1', sa.Integer(), nullable=True),
            sa.Column('ro2', sa.Integer(), nullable=True),
            sa.Column('editing_by', sa.String(length=255), nullable=True),
            sa.Column('version_no', sa.Integer(), nullable=False, server_default='0'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index('idx_users_user_id', 'users', ['user_id'], unique=True)
        op.create_index('idx_users_user_name', 'users', ['user_name'], unique=False)
        op.create_index('idx_users_user_email', 'users', ['user_email'], unique=False)
        op.create_index('idx_users_user_staffcode', 'users', ['user_staffcode'], unique=False)
        op.create_index('idx_users_user_employee_id', 'users', ['user_employee_id'], unique=False)
        op.create_index('idx_users_user_employee_number', 'users', ['user_employee_number'], unique=False)
        op.create_index('idx_users_user_is_deleted', 'users', ['user_is_deleted'], unique=False)
        op.create_index('idx_users_user_is_disabled', 'users', ['user_is_disabled'], unique=False)
        op.create_index('idx_users_agent_id', 'users', ['agent_id'], unique=False)
        op.create_index('idx_users_company_id', 'users', ['company_id'], unique=False)
        op.create_index('idx_users_user_department_id', 'users', ['user_department_id'], unique=False)
        op.create_index('idx_users_user_branch_id', 'users', ['user_branch_id'], unique=False)
        op.create_index('idx_users_supervisor_user_id', 'users', ['supervisor_user_id'], unique=False)
        op.create_index('idx_users_backup_user_id', 'users', ['backup_user_id'], unique=False)
        
        # Step 2: Migrate data from old table to new table (if needed)
        # This is a simple migration that maps old fields to new fields where possible
        op.execute("""
            INSERT INTO users (
                user_id, user_name, user_password, user_email, 
                user_firstname, user_lastname, user_created_on, user_modified_on
            )
            SELECT 
                id as user_id,
                username as user_name,
                hashed_password as user_password,
                email as user_email,
                CASE 
                    WHEN full_name IS NOT NULL AND instr(full_name, ' ') > 0 
                    THEN substr(full_name, 1, instr(full_name, ' ') - 1)
                    ELSE full_name
                END as user_firstname,
                CASE 
                    WHEN full_name IS NOT NULL AND instr(full_name, ' ') > 0 
                    THEN substr(full_name, instr(full_name, ' ') + 1)
                    ELSE NULL
                END as user_lastname,
                created_at as user_created_on,
                updated_at as user_modified_on
            FROM users_backup
            WHERE EXISTS (SELECT 1 FROM users_backup LIMIT 1)
        """)
        
        # Step 3: Drop the backup table (optional - comment this out if you want to keep it)
        # op.drop_table('users_backup')
        
    else:
        # If users table doesn't exist, create it fresh
        op.create_table(
            'users',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('agent_id', sa.BigInteger(), nullable=True),
            sa.Column('company_id', sa.BigInteger(), nullable=True),
            sa.Column('user_nric', sa.String(length=50), nullable=True),
            sa.Column('user_name', sa.String(length=255), nullable=False),
            sa.Column('user_initial', sa.String(length=10), nullable=True),
            sa.Column('user_password', sa.String(length=500), nullable=False),
            sa.Column('user_email', sa.String(length=255), nullable=True),
            sa.Column('user_firstname', sa.String(length=255), nullable=True),
            sa.Column('user_lastname', sa.String(length=255), nullable=True),
            sa.Column('user_gender', sa.String(length=20), nullable=True),
            sa.Column('user_maritalstatus', sa.String(length=50), nullable=True),
            sa.Column('user_department_id', sa.BigInteger(), nullable=True),
            sa.Column('user_branch_id', sa.BigInteger(), nullable=True),
            sa.Column('user_officephone', sa.String(length=50), nullable=True),
            sa.Column('user_homephone', sa.String(length=50), nullable=True),
            sa.Column('user_handphone', sa.String(length=50), nullable=True),
            sa.Column('user_address1', sa.String(length=500), nullable=True),
            sa.Column('user_address2', sa.String(length=500), nullable=True),
            sa.Column('user_addresscity', sa.String(length=100), nullable=True),
            sa.Column('user_stateprovince', sa.String(length=100), nullable=True),
            sa.Column('user_postalcode', sa.String(length=20), nullable=True),
            sa.Column('user_citycode', sa.String(length=20), nullable=True),
            sa.Column('user_countrycode', sa.String(length=20), nullable=True),
            sa.Column('user_note', sa.Text(), nullable=True),
            sa.Column('user_is_deleted', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('user_is_disabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_show', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('is_update', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_ad_user', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('user_register_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_created_by', sa.String(length=255), nullable=True),
            sa.Column('user_created_on', sa.DateTime(timezone=True), nullable=False),
            sa.Column('user_modified_by', sa.String(length=255), nullable=True),
            sa.Column('user_modified_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_photo_path', sa.String(length=1000), nullable=True),
            sa.Column('user_signature_path', sa.String(length=1000), nullable=True),
            sa.Column('user_is_firsttime_login', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('user_security_question_id', sa.BigInteger(), nullable=True),
            sa.Column('user_security_answer', sa.String(length=500), nullable=True),
            sa.Column('user_is_trustedhub', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('user_staffcode', sa.String(length=50), nullable=True),
            sa.Column('user_employee_id', sa.String(length=50), nullable=True),
            sa.Column('user_employee_number', sa.String(length=50), nullable=True),
            sa.Column('job_title', sa.String(length=255), nullable=True),
            sa.Column('staff_type', sa.String(length=100), nullable=True),
            sa.Column('highest_education', sa.String(length=255), nullable=True),
            sa.Column('join_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_approval_limit', sa.DECIMAL(18, 2), nullable=True),
            sa.Column('user_deviation_limit', sa.DECIMAL(18, 2), nullable=True),
            sa.Column('supervisor_user_id', sa.Integer(), nullable=True),
            sa.Column('backup_user_id', sa.Integer(), nullable=True),
            sa.Column('user_notification_emails', sa.Text(), nullable=True),
            sa.Column('user_deleted_by', sa.String(length=255), nullable=True),
            sa.Column('user_deleted_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_reset_password_by', sa.String(length=255), nullable=True),
            sa.Column('user_reset_password_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_disabled_by', sa.String(length=255), nullable=True),
            sa.Column('user_disabled_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_enabled_by', sa.String(length=255), nullable=True),
            sa.Column('user_enabled_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('user_change_password_by', sa.String(length=255), nullable=True),
            sa.Column('user_change_password_on', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ro1', sa.Integer(), nullable=True),
            sa.Column('ro2', sa.Integer(), nullable=True),
            sa.Column('editing_by', sa.String(length=255), nullable=True),
            sa.Column('version_no', sa.Integer(), nullable=False, server_default='0'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index('idx_users_user_id', 'users', ['user_id'], unique=True)
        op.create_index('idx_users_user_name', 'users', ['user_name'], unique=False)
        op.create_index('idx_users_user_email', 'users', ['user_email'], unique=False)
        op.create_index('idx_users_user_staffcode', 'users', ['user_staffcode'], unique=False)
        op.create_index('idx_users_user_employee_id', 'users', ['user_employee_id'], unique=False)
        op.create_index('idx_users_user_employee_number', 'users', ['user_employee_number'], unique=False)
        op.create_index('idx_users_user_is_deleted', 'users', ['user_is_deleted'], unique=False)
        op.create_index('idx_users_user_is_disabled', 'users', ['user_is_disabled'], unique=False)
        op.create_index('idx_users_agent_id', 'users', ['agent_id'], unique=False)
        op.create_index('idx_users_company_id', 'users', ['company_id'], unique=False)
        op.create_index('idx_users_user_department_id', 'users', ['user_department_id'], unique=False)
        op.create_index('idx_users_user_branch_id', 'users', ['user_branch_id'], unique=False)
        op.create_index('idx_users_supervisor_user_id', 'users', ['supervisor_user_id'], unique=False)
        op.create_index('idx_users_backup_user_id', 'users', ['backup_user_id'], unique=False)


def downgrade() -> None:
    """
    Downgrade the user table structure.
    
    This will restore the simple auth model structure.
    WARNING: This will lose data from the extended fields.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Drop all indexes
    op.drop_index('idx_users_backup_user_id', table_name='users')
    op.drop_index('idx_users_supervisor_user_id', table_name='users')
    op.drop_index('idx_users_user_branch_id', table_name='users')
    op.drop_index('idx_users_user_department_id', table_name='users')
    op.drop_index('idx_users_company_id', table_name='users')
    op.drop_index('idx_users_agent_id', table_name='users')
    op.drop_index('idx_users_user_is_disabled', table_name='users')
    op.drop_index('idx_users_user_is_deleted', table_name='users')
    op.drop_index('idx_users_user_employee_number', table_name='users')
    op.drop_index('idx_users_user_employee_id', table_name='users')
    op.drop_index('idx_users_user_staffcode', table_name='users')
    op.drop_index('idx_users_user_email', table_name='users')
    op.drop_index('idx_users_user_name', table_name='users')
    op.drop_index('idx_users_user_id', table_name='users')
    
    # Drop the new users table
    op.drop_table('users')
    
    # Restore the old table structure if backup exists
    if 'users_backup' in inspector.get_table_names():
        op.rename_table('users_backup', 'users')

