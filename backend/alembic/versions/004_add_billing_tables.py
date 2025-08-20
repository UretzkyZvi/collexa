"""Add billing tables for payment-agnostic billing system

Revision ID: 004_add_billing_tables
Revises: 003_add_sandbox_tables
Create Date: 2025-01-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_billing_tables'
down_revision = '003_add_sandbox_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create billing_customers table
    op.create_table('billing_customers',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('org_id', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('external_customer_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create billing_subscriptions table
    op.create_table('billing_subscriptions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('customer_id', sa.String(length=64), nullable=False),
        sa.Column('external_subscription_id', sa.String(length=255), nullable=False),
        sa.Column('plan_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['billing_customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create billing_events table
    op.create_table('billing_events',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('org_id', sa.String(length=64), nullable=False),
        sa.Column('customer_id', sa.String(length=64), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('external_event_id', sa.String(length=255), nullable=True),
        sa.Column('amount_cents', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['billing_customers.id'], ),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create budgets table
    op.create_table('budgets',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('org_id', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.String(length=64), nullable=True),
        sa.Column('period', sa.String(length=32), nullable=False),
        sa.Column('limit_cents', sa.Integer(), nullable=False),
        sa.Column('current_usage_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('alerts_json', sa.JSON(), nullable=True),
        sa.Column('enforcement_mode', sa.String(length=16), nullable=False, server_default='soft'),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create usage_records table
    op.create_table('usage_records',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('org_id', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.String(length=64), nullable=True),
        sa.Column('run_id', sa.String(length=64), nullable=True),
        sa.Column('usage_type', sa.String(length=32), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('cost_cents', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('billing_period', sa.String(length=32), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better query performance
    op.create_index('ix_billing_customers_org_id', 'billing_customers', ['org_id'])
    op.create_index('ix_billing_customers_external_id', 'billing_customers', ['external_customer_id'])
    op.create_index('ix_billing_subscriptions_customer_id', 'billing_subscriptions', ['customer_id'])
    op.create_index('ix_billing_subscriptions_external_id', 'billing_subscriptions', ['external_subscription_id'])
    op.create_index('ix_billing_subscriptions_status', 'billing_subscriptions', ['status'])
    op.create_index('ix_billing_events_org_id', 'billing_events', ['org_id'])
    op.create_index('ix_billing_events_event_type', 'billing_events', ['event_type'])
    op.create_index('ix_billing_events_external_id', 'billing_events', ['external_event_id'])
    op.create_index('ix_budgets_org_id', 'budgets', ['org_id'])
    op.create_index('ix_budgets_agent_id', 'budgets', ['agent_id'])
    op.create_index('ix_budgets_status', 'budgets', ['status'])
    op.create_index('ix_usage_records_org_id', 'usage_records', ['org_id'])
    op.create_index('ix_usage_records_agent_id', 'usage_records', ['agent_id'])
    op.create_index('ix_usage_records_billing_period', 'usage_records', ['billing_period'])
    op.create_index('ix_usage_records_usage_type', 'usage_records', ['usage_type'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_usage_records_usage_type', table_name='usage_records')
    op.drop_index('ix_usage_records_billing_period', table_name='usage_records')
    op.drop_index('ix_usage_records_agent_id', table_name='usage_records')
    op.drop_index('ix_usage_records_org_id', table_name='usage_records')
    op.drop_index('ix_budgets_status', table_name='budgets')
    op.drop_index('ix_budgets_agent_id', table_name='budgets')
    op.drop_index('ix_budgets_org_id', table_name='budgets')
    op.drop_index('ix_billing_events_external_id', table_name='billing_events')
    op.drop_index('ix_billing_events_event_type', table_name='billing_events')
    op.drop_index('ix_billing_events_org_id', table_name='billing_events')
    op.drop_index('ix_billing_subscriptions_status', table_name='billing_subscriptions')
    op.drop_index('ix_billing_subscriptions_external_id', table_name='billing_subscriptions')
    op.drop_index('ix_billing_subscriptions_customer_id', table_name='billing_subscriptions')
    op.drop_index('ix_billing_customers_external_id', table_name='billing_customers')
    op.drop_index('ix_billing_customers_org_id', table_name='billing_customers')

    # Drop tables
    op.drop_table('usage_records')
    op.drop_table('budgets')
    op.drop_table('billing_events')
    op.drop_table('billing_subscriptions')
    op.drop_table('billing_customers')
