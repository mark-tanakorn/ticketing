"""unified_status_system

Revision ID: 003
Revises: 002
Create Date: 2025-11-03 16:00:00.000000

Changes:
- Workflows table:
  - Remove: monitoring_state column
  - Add: status column (default='na')
  - Add: last_execution_id column (FK to executions)
  - Update indexes
- Executions table:
  - Update: execution_mode default from 'parallel' to 'oneshot'
  - Update: status values (cancelled → stopped)

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '003_unified_status'
down_revision = '002_update_user_fks'
branch_labels = None
depends_on = None


def upgrade():
    """Apply unified status system changes"""
    
    # ==========================================================================
    # WORKFLOWS TABLE CHANGES
    # ==========================================================================
    
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        # Add new columns
        batch_op.add_column(sa.Column('status', sa.String(50), nullable=False, server_default='na'))
        batch_op.add_column(sa.Column('last_execution_id', sa.String(36), nullable=True))
        
        # Drop old column and its index
        batch_op.drop_index('idx_workflows_monitoring_state')
        batch_op.drop_column('monitoring_state')
        
        # Add new indexes
        batch_op.create_index('idx_workflows_status', ['status'])
        batch_op.create_index('idx_workflows_last_execution_id', ['last_execution_id'])
        
        # Add foreign key constraint
        batch_op.create_foreign_key(
            'fk_workflows_last_execution_id',
            'executions',
            ['last_execution_id'],
            ['id'],
            ondelete='SET NULL'
        )
    
    # ==========================================================================
    # EXECUTIONS TABLE CHANGES
    # ==========================================================================
    
    with op.batch_alter_table('executions', schema=None) as batch_op:
        # Update execution_mode default value
        # Note: This only affects NEW rows, existing rows keep their values
        batch_op.alter_column(
            'execution_mode',
            existing_type=sa.String(20),
            server_default='oneshot',
            existing_nullable=False
        )
    
    # ==========================================================================
    # DATA MIGRATION
    # ==========================================================================
    
    # Update existing workflows: map monitoring_state values to status
    # Note: This is a best-effort migration based on the old monitoring_state
    connection = op.get_bind()
    
    # For SQLite, we need to read and update (can't do complex UPDATE with CASE)
    workflows = connection.execute(sa.text("SELECT id FROM workflows")).fetchall()
    
    # All existing workflows get 'na' status (they can be re-activated if needed)
    # This is the safest default since we can't determine their actual state
    for workflow in workflows:
        connection.execute(
            sa.text("UPDATE workflows SET status = 'na' WHERE id = :id"),
            {"id": workflow[0]}
        )
    
    # Update existing executions: change 'cancelled' to 'stopped'
    connection.execute(
        sa.text("UPDATE executions SET status = 'stopped' WHERE status = 'cancelled'")
    )
    
    connection.commit()


def downgrade():
    """Revert unified status system changes"""
    
    # ==========================================================================
    # WORKFLOWS TABLE ROLLBACK
    # ==========================================================================
    
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        # Drop new columns and indexes
        batch_op.drop_constraint('fk_workflows_last_execution_id', type_='foreignkey')
        batch_op.drop_index('idx_workflows_last_execution_id')
        batch_op.drop_index('idx_workflows_status')
        batch_op.drop_column('last_execution_id')
        batch_op.drop_column('status')
        
        # Restore old column
        batch_op.add_column(
            sa.Column('monitoring_state', sa.String(20), nullable=False, server_default='inactive')
        )
        batch_op.create_index('idx_workflows_monitoring_state', ['monitoring_state'])
    
    # ==========================================================================
    # EXECUTIONS TABLE ROLLBACK
    # ==========================================================================
    
    with op.batch_alter_table('executions', schema=None) as batch_op:
        # Revert execution_mode default
        batch_op.alter_column(
            'execution_mode',
            existing_type=sa.String(20),
            server_default='parallel',
            existing_nullable=False
        )
    
    # ==========================================================================
    # DATA ROLLBACK
    # ==========================================================================
    
    connection = op.get_bind()
    
    # Revert status changes in executions
    connection.execute(
        sa.text("UPDATE executions SET status = 'cancelled' WHERE status = 'stopped'")
    )
    
    connection.commit()

