"""add a2a_manifests table

Revision ID: 0006_a2a_manifests
Revises: 0005_audit_logs
Create Date: 2025-08-19
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_a2a_manifests"
down_revision = "0005_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "a2a_manifests",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=16), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_a2a_manifests_agent", "a2a_manifests", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_a2a_manifests_agent", table_name="a2a_manifests")
    op.drop_table("a2a_manifests")
