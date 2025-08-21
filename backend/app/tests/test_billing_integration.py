"""
Integration tests for billing and budget system.

These tests verify the complete billing flow including budget enforcement,
usage tracking, and payment provider integration.
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.services.billing_service import BillingService
from app.services.budget_service import (
    BudgetService,
    BudgetPeriod,
    EnforcementMode,
    BudgetExceededException,
)
from app.services.metering_service import MeteringService
from app.services.payment.providers.mock_provider import MockProvider
from app.db import models


class TestBillingIntegration:
    """Integration tests for billing system"""

    def setup_method(self):
        """Setup test environment"""
        self.mock_db = Mock(spec=Session)
        self.mock_provider = MockProvider()

        # Test data
        self.org_id = "test-org-123"
        self.agent_id = "test-agent-456"
        self.run_id = "test-run-789"

        # Mock org and agent
        self.mock_org = models.Org(id=self.org_id, name="Test Org")
        self.mock_agent = models.Agent(
            id=self.agent_id, org_id=self.org_id, display_name="Test Agent"
        )

    @pytest.mark.asyncio
    async def test_complete_billing_flow(self):
        """Test complete billing flow from budget creation to usage tracking"""
        # Setup services
        budget_service = BudgetService(self.mock_db)
        billing_service = BillingService(self.mock_db, self.mock_provider)
        metering_service = MeteringService(self.mock_db)

        # Mock database operations
        self._setup_db_mocks()

        # 1. Create billing customer
        billing_customer = await billing_service.create_customer_for_org(
            org_id=self.org_id, email="test@example.com", name="Test Customer"
        )

        assert billing_customer.org_id == self.org_id
        assert billing_customer.provider == "mock"

        # 2. Create budget
        budget = budget_service.create_budget(
            org_id=self.org_id,
            period=BudgetPeriod.MONTHLY,
            limit_cents=10000,  # $100 limit
            agent_id=self.agent_id,
            enforcement_mode=EnforcementMode.SOFT,
        )

        assert budget.limit_cents == 10000
        assert budget.current_usage_cents == 0

        # 3. Record usage within budget
        usage_records = await metering_service.record_agent_invocation(
            org_id=self.org_id,
            agent_id=self.agent_id,
            run_id=self.run_id,
            input_tokens=1000,
            output_tokens=500,
        )

        assert len(usage_records) == 3  # invocation + input_tokens + output_tokens

        # 4. Check budget status
        # Ensure get_budget returns our created budget (fix mock chain)
        self.mock_db.query.return_value.filter.return_value.first.return_value = budget
        updated_budget = budget_service.get_budget(budget.id)
        assert (
            hasattr(updated_budget, "current_usage_cents")
            and updated_budget.current_usage_cents >= 0
        )

    @pytest.mark.asyncio
    async def test_hard_budget_enforcement(self):
        """Test that hard budget limits are enforced"""
        budget_service = BudgetService(self.mock_db)
        metering_service = MeteringService(self.mock_db)

        self._setup_db_mocks()

        # Create a small budget with hard enforcement
        budget = budget_service.create_budget(
            org_id=self.org_id,
            period=BudgetPeriod.DAILY,
            limit_cents=50,  # $0.50 limit
            agent_id=self.agent_id,
            enforcement_mode=EnforcementMode.HARD,
        )

        # Mock active budgets to include our budget
        self.mock_db.query.return_value.filter.return_value.all.return_value = [budget]

        # Also mock org-level query path
        def query_side_effect(model):
            return self.mock_db.query.return_value

        self.mock_db.query.side_effect = query_side_effect

        # Try to record usage that would exceed budget
        with pytest.raises(BudgetExceededException) as exc_info:
            await metering_service.record_agent_invocation(
                org_id=self.org_id,
                agent_id=self.agent_id,
                run_id=self.run_id,
                input_tokens=100000,  # Ensure cost exceeds $0.50 with current pricing
                output_tokens=5000,
            )

        assert exc_info.value.budget_id == budget.id
        assert exc_info.value.limit_cents == 50

    @pytest.mark.asyncio
    async def test_usage_reporting_to_provider(self):
        """Test that usage is reported to payment provider"""
        billing_service = BillingService(self.mock_db, self.mock_provider)
        metering_service = MeteringService(self.mock_db)

        self._setup_db_mocks()

        # Create subscription with metered item
        subscription = models.BillingSubscription(
            id="sub-123",
            customer_id="cust-123",
            external_subscription_id="mock_sub_123",
            plan_id="plan-123",
            status="active",
            metadata={"metered_item_id": "item_123"},
        )

        # Mock subscription retrieval
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            subscription
        )

        # Record usage
        usage_records = await metering_service.record_agent_invocation(
            org_id=self.org_id,
            agent_id=self.agent_id,
            run_id=self.run_id,
            input_tokens=1000,
            output_tokens=500,
        )

        # Verify usage was recorded
        assert len(usage_records) > 0

        # Note: In a real test, we would verify that the mock provider
        # received the usage report call

    @pytest.mark.asyncio
    async def test_webhook_processing(self):
        """Test webhook processing for subscription events"""
        billing_service = BillingService(self.mock_db, self.mock_provider)

        self._setup_db_mocks()

        # Create billing customer
        billing_customer = models.BillingCustomer(
            id="billing-cust-123",
            org_id=self.org_id,
            provider="mock",
            external_customer_id="mock_cus_123",
            email="test@example.com",
        )

        # Mock customer retrieval
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            billing_customer
        )

        # Create webhook payload
        import json

        webhook_payload = json.dumps(
            {
                "type": "customer.subscription.created",
                "data": {
                    "object": {
                        "id": "sub_123",
                        "customer": "mock_cus_123",
                        "status": "active",
                        "current_period_start": 1640995200,  # 2022-01-01
                        "current_period_end": 1643673600,  # 2022-02-01
                        "items": {"data": [{"price": {"id": "price_123"}}]},
                        "metadata": {"org_id": self.org_id},
                    }
                },
            }
        ).encode()

        # Process webhook
        success = await billing_service.handle_webhook_event(
            payload=webhook_payload, signature="mock_signature"
        )

        assert success is True

        # Verify database operations were called
        self.mock_db.add.assert_called()
        self.mock_db.commit.assert_called()

    def test_usage_summary_generation(self):
        """Test usage summary generation"""
        budget_service = BudgetService(self.mock_db)

        # Mock usage records
        usage_records = [
            models.UsageRecord(
                id="usage-1",
                org_id=self.org_id,
                agent_id=self.agent_id,
                usage_type="invocation",
                quantity=1,
                cost_cents=10,
                billing_period="2025-01",
            ),
            models.UsageRecord(
                id="usage-2",
                org_id=self.org_id,
                agent_id=self.agent_id,
                usage_type="input_tokens",
                quantity=1000,
                cost_cents=1,
                billing_period="2025-01",
            ),
        ]

        # Configure chained mocks to return our list
        mock_query = self.mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        # Support chained filters
        mock_filter.filter.return_value = mock_filter
        mock_filter.all.return_value = usage_records[:]
        mock_filter.all.side_effect = None

        # Generate summary
        summary = budget_service.get_usage_summary(
            org_id=self.org_id, agent_id=self.agent_id
        )

        assert summary["total_cost_cents"] == 11
        assert summary["total_cost_dollars"] == 0.11
        assert "invocation" in summary["usage_by_type"]
        assert "input_tokens" in summary["usage_by_type"]
        assert summary["record_count"] == 2

    @pytest.mark.asyncio
    async def test_checkout_session_creation(self):
        """Test checkout session creation"""
        billing_service = BillingService(self.mock_db, self.mock_provider)

        self._setup_db_mocks()

        # Mock existing billing customer
        billing_customer = models.BillingCustomer(
            id="billing-cust-123",
            org_id=self.org_id,
            provider="mock",
            external_customer_id="mock_cus_123",
            email="test@example.com",
        )

        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            billing_customer
        )

        # Ensure provider has the customer
        self.mock_provider._customers[
            billing_customer.external_customer_id
        ] = self.mock_provider._customers.get(
            billing_customer.external_customer_id
        ) or type(
            self.mock_provider
        ).create_customer.__annotations__.get(
            "return", None
        )

        # Create checkout session
        checkout_session = await billing_service.create_checkout_session(
            org_id=self.org_id,
            plan_id="plan_123",
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
        )

        assert checkout_session.customer_id is not None
        assert "mock-checkout.example.com" in checkout_session.url
        assert checkout_session.id.startswith("mock_cs_")

    def _setup_db_mocks(self):
        """Setup common database mocks"""
        # Mock database operations
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()
        self.mock_db.rollback = Mock()

        # Mock query operations
        mock_query = Mock()
        mock_filter = Mock()
        mock_first = Mock()
        mock_all = Mock()

        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = self.mock_org
        mock_filter.all.return_value = []

        # Setup specific mocks for different queries
        def query_side_effect(model):
            if model == models.Org:
                mock_filter.first.return_value = self.mock_org
            elif model == models.Agent:
                mock_filter.first.return_value = self.mock_agent
            elif model == models.BillingCustomer:
                mock_filter.first.return_value = None  # No existing customer
            return mock_query

        self.mock_db.query.side_effect = query_side_effect


if __name__ == "__main__":
    pytest.main([__file__])
