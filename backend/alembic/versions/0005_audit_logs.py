"""audit logs table

Revision ID: 0005_audit_logs
Revises: 0004_agent_keys
Create Date: 2025-08-18
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_audit_logs"
down_revision = "0004_agent_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("capability", sa.String(length=255), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    # Index for common queries
    op.create_index(
        "idx_audit_logs_org_created", "audit_logs", ["org_id", "created_at"]
    )
    op.create_index("idx_audit_logs_agent", "audit_logs", ["agent_id"])


def downgrade() -> None:
    op.drop_index("idx_audit_logs_agent")
    op.drop_index("idx_audit_logs_org_created")
    op.drop_table("audit_logs")
