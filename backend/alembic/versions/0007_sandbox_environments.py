"""sandbox environments

Revision ID: 0007
Revises: 0006
Create Date: 2025-08-19 06:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0007_sandbox_environments'
down_revision = '0006_a2a_manifests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sandboxes table
    op.create_table('sandboxes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('mode', sa.String(), nullable=False),  # mock, emulated, connected
        sa.Column('target_system', sa.String(), nullable=True),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='created'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sandboxes_agent_id'), 'sandboxes', ['agent_id'], unique=False)
    op.create_index(op.f('ix_sandboxes_org_id'), 'sandboxes', ['org_id'], unique=False)
    
    # Create sandbox_runs table
    op.create_table('sandbox_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('sandbox_id', sa.String(), nullable=False),
        sa.Column('phase', sa.String(), nullable=False),  # learn, eval
        sa.Column('task_name', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='running'),
        sa.Column('input_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['sandbox_id'], ['sandboxes.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_sandbox_runs_sandbox_id'), 'sandbox_runs', ['sandbox_id'], unique=False)
    
    # Create learning_plans table
    op.create_table('learning_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('target_system', sa.String(), nullable=True),
        sa.Column('objectives_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('curriculum_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_learning_plans_agent_id'), 'learning_plans', ['agent_id'], unique=False)
    
    # Create capability_assessments table
    op.create_table('capability_assessments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('target_system', sa.String(), nullable=True),
        sa.Column('rubric_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_run_ids', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_capability_assessments_agent_id'), 'capability_assessments', ['agent_id'], unique=False)
    
    # Add RLS policies for tenant isolation
    op.execute("""
        ALTER TABLE sandboxes ENABLE ROW LEVEL SECURITY;
        CREATE POLICY sandboxes_org_isolation ON sandboxes
            USING (org_id = current_setting('app.org_id', true));
    """)
    
    op.execute("""
        ALTER TABLE sandbox_runs ENABLE ROW LEVEL SECURITY;
        CREATE POLICY sandbox_runs_org_isolation ON sandbox_runs
            USING (EXISTS (
                SELECT 1 FROM sandboxes 
                WHERE sandboxes.id = sandbox_runs.sandbox_id 
                AND sandboxes.org_id = current_setting('app.org_id', true)
            ));
    """)
    
    op.execute("""
        ALTER TABLE learning_plans ENABLE ROW LEVEL SECURITY;
        CREATE POLICY learning_plans_org_isolation ON learning_plans
            USING (EXISTS (
                SELECT 1 FROM agents 
                WHERE agents.id = learning_plans.agent_id 
                AND agents.org_id = current_setting('app.org_id', true)
            ));
    """)
    
    op.execute("""
        ALTER TABLE capability_assessments ENABLE ROW LEVEL SECURITY;
        CREATE POLICY capability_assessments_org_isolation ON capability_assessments
            USING (EXISTS (
                SELECT 1 FROM agents 
                WHERE agents.id = capability_assessments.agent_id 
                AND agents.org_id = current_setting('app.org_id', true)
            ));
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS capability_assessments_org_isolation ON capability_assessments;")
    op.execute("DROP POLICY IF EXISTS learning_plans_org_isolation ON learning_plans;")
    op.execute("DROP POLICY IF EXISTS sandbox_runs_org_isolation ON sandbox_runs;")
    op.execute("DROP POLICY IF EXISTS sandboxes_org_isolation ON sandboxes;")
    
    # Drop tables
    op.drop_table('capability_assessments')
    op.drop_table('learning_plans')
    op.drop_table('sandbox_runs')
    op.drop_table('sandboxes')
