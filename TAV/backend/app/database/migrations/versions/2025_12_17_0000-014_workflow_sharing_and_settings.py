"""Add workflow ownership + sharing visibility + workflow settings

Revision ID: 014_workflow_sharing_and_settings
Revises: 013_add_conversation_message_activity
Create Date: 2025-12-17

This migration separates workflow ownership (who can see/manage it) from authorship
(credit) and adds a minimal sharing/status foundation plus a JSON settings blob for
workflow-specific settings (future-proof).

New columns on workflows:
- owner_id: user that owns this workflow copy (visibility / permissions key)
- visibility: private | link | public
- share_id: opaque id to support "selective share link" in future
- workflow_settings: per-workflow settings blob (JSON)
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "014_workflow_sharing_and_settings"
down_revision = "013_add_conversation_message_activity"
branch_labels = None
depends_on = None


def upgrade():
    """Add ownership + sharing + per-workflow settings."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "workflows" not in tables:
        return

    # 1) Add new columns (owner_id initially nullable for backfill)
    with op.batch_alter_table("workflows", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True, comment="Owner user id (visibility/permissions key)"))
        batch_op.add_column(sa.Column("visibility", sa.String(20), nullable=False, server_default="private", comment="private|link|public"))
        batch_op.add_column(sa.Column("share_id", sa.String(36), nullable=True, comment="Opaque id for selective share link"))
        batch_op.add_column(sa.Column("workflow_settings", sa.JSON(), nullable=True, comment="Per-workflow settings blob"))

        batch_op.create_index("idx_workflows_owner_id", ["owner_id"], unique=False)
        batch_op.create_index("idx_workflows_visibility", ["visibility"], unique=False)
        batch_op.create_index("idx_workflows_share_id", ["share_id"], unique=True)

    # 2) Backfill owner_id from existing author_id (legacy behavior used author_id as owner)
    op.execute(
        """
        UPDATE workflows
        SET owner_id = author_id
        WHERE owner_id IS NULL
        """
    )

    # 3) Enforce NOT NULL on owner_id after backfill
    with op.batch_alter_table("workflows", schema=None) as batch_op:
        batch_op.alter_column(
            "owner_id",
            existing_type=sa.Integer(),
            nullable=False
        )
        # Foreign key (matches author_id style: SET NULL is inappropriate for owner_id because it's non-null;
        # we keep it RESTRICT-ish by omitting ondelete behavior for now).
        batch_op.create_foreign_key(
            "fk_workflows_owner_id",
            "users",
            ["owner_id"],
            ["id"]
        )


def downgrade():
    """Remove ownership + sharing + per-workflow settings."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "workflows" not in tables:
        return

    with op.batch_alter_table("workflows", schema=None) as batch_op:
        batch_op.drop_constraint("fk_workflows_owner_id", type_="foreignkey")
        batch_op.drop_index("idx_workflows_share_id")
        batch_op.drop_index("idx_workflows_visibility")
        batch_op.drop_index("idx_workflows_owner_id")

        batch_op.drop_column("workflow_settings")
        batch_op.drop_column("share_id")
        batch_op.drop_column("visibility")
        batch_op.drop_column("owner_id")


