"""
Tests for refactored billing and usage services.

These tests verify that the smaller, focused services work correctly
and that the orchestrators coordinate them properly.
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.billing_orchestrator import BillingOrchestrator
from app.services.usage_orchestrator import UsageOrchestrator
from app.services.billing.customer_service import CustomerService
from app.services.billing.checkout_service import CheckoutService
from app.services.budget.budget_enforcement_service import (
    BudgetEnforcementService,
    BudgetExceededException,
)
from app.services.usage.cost_calculation_service import CostCalculationService
from app.services.payment.providers.mock_provider import MockProvider
from app.db import models


class TestRefactoredServices:
    """Test the refactored service architecture"""

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
    async def test_customer_service_isolation(self):
        """Test that CustomerService works independently"""
        customer_service = CustomerService(self.mock_db, self.mock_provider)

        # Mock database operations
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            self.mock_org
        )
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()

        # Create customer
        billing_customer = await customer_service.create_customer_for_org(
            org_id=self.org_id, email="test@example.com", name="Test Customer"
        )

        assert billing_customer.org_id == self.org_id
        assert billing_customer.provider == "mock"
        assert billing_customer.email == "test@example.com"

        # Verify database operations
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_checkout_service_isolation(self):
        """Test that CheckoutService works independently"""
        checkout_service = CheckoutService(self.mock_db, self.mock_provider)

        # Mock customer service dependency
        mock_billing_customer = models.BillingCustomer(
            id="billing-customer-123",
            org_id=self.org_id,
            provider="mock",
            external_customer_id="mock_cus_123",
            email="test@example.com",
        )

        with patch.object(
            checkout_service.customer_service, "get_or_create_customer_for_org"
        ) as mock_get_customer:
            mock_get_customer.return_value = mock_billing_customer

            # Ensure mock provider has the customer registered
            from app.services.payment.protocol import Customer

            self.mock_provider._customers[
                mock_billing_customer.external_customer_id
            ] = Customer(
                id=mock_billing_customer.external_customer_id,
                email=mock_billing_customer.email,
                name="Test Customer",
                metadata={"org_id": self.org_id},
            )

            checkout_session = await checkout_service.create_checkout_session(
                org_id=self.org_id,
                plan_id="test-plan-123",
                success_url="http://localhost:3000/success",
                cancel_url="http://localhost:3000/cancel",
            )

            assert checkout_session.customer_id is not None
            assert "mock-checkout.example.com" in checkout_session.url
            mock_get_customer.assert_called_once()

    def test_cost_calculation_service_isolation(self):
        """Test that CostCalculationService works independently"""
        cost_calculator = CostCalculationService()

        # Test basic cost calculation
        invocation_cost = cost_calculator.calculate_cost("invocation", 1)
        assert invocation_cost.usage_type == "invocation"
        assert invocation_cost.quantity == 1
        assert invocation_cost.cost_cents == 10  # Default rate

        # Test token cost calculation
        token_cost = cost_calculator.calculate_cost("input_tokens", 1000)
        assert token_cost.usage_type == "input_tokens"
        assert token_cost.quantity == 1000
        assert token_cost.cost_cents == 1  # 1000 tokens = 1 cent

        # Test invocation cost calculation
        invocation_costs = cost_calculator.calculate_invocation_cost(
            input_tokens=1000, output_tokens=500
        )

        assert len(invocation_costs) == 3  # invocation + input_tokens + output_tokens
        total_cost = cost_calculator.calculate_total_cost(invocation_costs)
        # 10 (invocation) + 1 (input 1000 @ 1c/1k) + 1 (output 500 @ 2c/1k)
        assert total_cost == 12

    def test_budget_enforcement_service_isolation(self):
        """Test that BudgetEnforcementService works independently"""
        budget_enforcement = BudgetEnforcementService(self.mock_db)

        # Mock budget data
        mock_budget = models.Budget(
            id="budget-123",
            org_id=self.org_id,
            agent_id=self.agent_id,
            period="daily",
            limit_cents=100,
            current_usage_cents=50,
            enforcement_mode="hard",
            status="active",
        )

        # Mock database query
        self.mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_budget
        ]

        # Test budget check - should pass
        result = budget_enforcement.check_budget_before_usage(
            org_id=self.org_id, estimated_cost_cents=30, agent_id=self.agent_id
        )
        assert result is True

        # Test budget check - should fail
        with pytest.raises(BudgetExceededException):
            budget_enforcement.check_budget_before_usage(
                org_id=self.org_id,
                estimated_cost_cents=60,  # Would exceed limit
                agent_id=self.agent_id,
            )

    @pytest.mark.asyncio
    async def test_billing_orchestrator_coordination(self):
        """Test that BillingOrchestrator coordinates services correctly"""
        billing_orchestrator = BillingOrchestrator(self.mock_db, self.mock_provider)

        # Mock database operations
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            self.mock_org
        )
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()

        # Test organization billing setup
        billing_customer = await billing_orchestrator.setup_organization_billing(
            org_id=self.org_id, email="test@example.com", name="Test Org"
        )

        assert billing_customer.org_id == self.org_id
        assert billing_customer.provider == "mock"

        # Ensure subsequent queries return the newly created billing customer
        def query_side_effect(model):
            from unittest.mock import Mock as _Mock

            mock_query = _Mock()
            mock_filter = _Mock()
            mock_query.filter.return_value = mock_filter
            if model == models.Org:
                mock_filter.first.return_value = self.mock_org
            elif model == models.BillingCustomer:
                mock_filter.first.return_value = billing_customer
            else:
                mock_filter.first.return_value = None
            return mock_query

        self.mock_db.query.side_effect = query_side_effect

        # Test checkout creation
        checkout_session = await billing_orchestrator.create_subscription_checkout(
            org_id=self.org_id,
            plan_id="test-plan",
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
        )

        assert checkout_session.customer_id is not None
        assert checkout_session.url is not None

    @pytest.mark.asyncio
    async def test_usage_orchestrator_coordination(self):
        """Test that UsageOrchestrator coordinates services correctly"""
        usage_orchestrator = UsageOrchestrator(self.mock_db, self.mock_provider)

        # Mock database operations
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()

        # Mock budget enforcement (no budgets = no restrictions)
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

        # Test agent invocation recording
        usage_records = await usage_orchestrator.record_agent_invocation(
            org_id=self.org_id,
            agent_id=self.agent_id,
            run_id=self.run_id,
            input_tokens=1000,
            output_tokens=500,
        )

        assert len(usage_records) == 3  # invocation + input_tokens + output_tokens

        # Verify database operations
        assert self.mock_db.add.call_count == 3  # One for each usage record
        self.mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_service_integration_flow(self):
        """Test complete flow using multiple services"""
        # Setup services
        billing_orchestrator = BillingOrchestrator(self.mock_db, self.mock_provider)
        usage_orchestrator = UsageOrchestrator(self.mock_db, self.mock_provider)

        # Mock database operations
        self._setup_db_mocks()

        # 1. Setup billing for organization
        billing_customer = await billing_orchestrator.setup_organization_billing(
            org_id=self.org_id, email="test@example.com", name="Test Org"
        )

        # 2. Create checkout session
        checkout_session = await billing_orchestrator.create_subscription_checkout(
            org_id=self.org_id,
            plan_id="test-plan",
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
        )

        # 3. Record usage (no budgets, so should succeed)
        usage_records = await usage_orchestrator.record_agent_invocation(
            org_id=self.org_id,
            agent_id=self.agent_id,
            run_id=self.run_id,
            input_tokens=1000,
            output_tokens=500,
        )

        # Verify all operations succeeded
        assert billing_customer.org_id == self.org_id
        assert checkout_session.customer_id is not None
        assert len(usage_records) == 3

    def test_service_dependencies_are_clear(self):
        """Test that service dependencies are explicit and minimal"""
        # CustomerService should have no dependencies on other billing services
        customer_service = CustomerService(self.mock_db, self.mock_provider)
        assert hasattr(customer_service, "db")
        assert hasattr(customer_service, "payment_provider")
        assert not hasattr(customer_service, "subscription_service")
        assert not hasattr(customer_service, "checkout_service")

        # CheckoutService should depend on CustomerService
        checkout_service = CheckoutService(self.mock_db, self.mock_provider)
        assert hasattr(checkout_service, "customer_service")
        assert not hasattr(checkout_service, "subscription_service")

        # BudgetEnforcementService should have minimal dependencies
        budget_enforcement = BudgetEnforcementService(self.mock_db)
        assert hasattr(budget_enforcement, "db")
        assert not hasattr(budget_enforcement, "payment_provider")

        # CostCalculationService should have no external dependencies
        cost_calculator = CostCalculationService()
        assert not hasattr(cost_calculator, "db")
        assert not hasattr(cost_calculator, "payment_provider")

    def _setup_db_mocks(self):
        """Setup common database mocks"""
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()
        self.mock_db.rollback = Mock()

        # Mock query operations
        mock_query = Mock()
        mock_filter = Mock()

        self.mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = self.mock_org
        mock_filter.all.return_value = []  # No budgets by default

        # Setup specific mocks for different queries
        def query_side_effect(model):
            if model == models.Org:
                mock_filter.first.return_value = self.mock_org
            elif model == models.Agent:
                mock_filter.first.return_value = self.mock_agent
            elif model == models.BillingCustomer:
                mock_filter.first.return_value = None  # No existing customer
            elif model == models.Budget:
                mock_filter.all.return_value = []  # No budgets
            return mock_query

        self.mock_db.query.side_effect = query_side_effect


if __name__ == "__main__":
    pytest.main([__file__])
