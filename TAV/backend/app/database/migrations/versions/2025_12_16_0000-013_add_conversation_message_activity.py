"""Add activity trace to conversation_messages

Revision ID: 013_add_conversation_message_activity
Revises: 012_custom_node_conversations
Create Date: 2025-12-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "013_add_conversation_message_activity"
down_revision = "012_custom_node_conversations"
branch_labels = None
depends_on = None


def upgrade():
    """Add activity JSON column to conversation_messages for UI trace persistence."""
    op.add_column("conversation_messages", sa.Column("activity", sa.JSON(), nullable=True))


def downgrade():
    """Remove activity JSON column."""
    op.drop_column("conversation_messages", "activity")



