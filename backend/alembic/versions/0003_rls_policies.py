"""RLS policies for agents, runs, logs (PoC)

Revision ID: 0003_rls_policies
Revises: 0002_orgs_runs_logs
Create Date: 2025-08-17 00:30:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_rls_policies"
down_revision = "0002_orgs_runs_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS and create policies if Postgres; no-op on SQLite
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # Enable RLS on core tables
    op.execute("ALTER TABLE agents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE logs ENABLE ROW LEVEL SECURITY")

    # Create org isolation policies
    op.execute(
        "CREATE POLICY org_isolation_agents ON agents USING (org_id = current_setting('app.org_id', true)::text)"
    )
    op.execute(
        "CREATE POLICY org_isolation_runs ON runs USING (org_id = current_setting('app.org_id', true)::text)"
    )
    # logs join on run_id -> ensure run belongs to org
    op.execute(
        "CREATE POLICY org_isolation_logs ON logs USING (EXISTS (SELECT 1 FROM runs r WHERE r.id = logs.run_id AND r.org_id = current_setting('app.org_id', true)::text))"
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    # Drop policies (optional)
    op.execute("DROP POLICY IF EXISTS org_isolation_logs ON logs")
    op.execute("DROP POLICY IF EXISTS org_isolation_runs ON runs")
    op.execute("DROP POLICY IF EXISTS org_isolation_agents ON agents")
