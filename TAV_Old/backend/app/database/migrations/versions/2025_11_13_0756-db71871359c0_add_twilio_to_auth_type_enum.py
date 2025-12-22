"""add_twilio_to_auth_type_enum

Revision ID: db71871359c0
Revises: 005_add_credentials
Create Date: 2025-11-13 07:56:05.776593+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db71871359c0'
down_revision = '005_add_credentials'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'twilio' to the authtype enum
    # For SQLite: No database change needed - enum is handled by Python code
    # For PostgreSQL: Would need ALTER TYPE command
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        op.execute("ALTER TYPE authtype ADD VALUE IF NOT EXISTS 'twilio'")
    # For SQLite, the enum is enforced by Python/SQLAlchemy, no DB change needed


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # SQLite doesn't need any changes
    pass

