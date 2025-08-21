"""
Tests for payment-agnostic billing system.

These tests demonstrate how the billing system works with different
payment providers without changing business logic.
"""

import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from app.services.billing_service import BillingService
from app.services.payment.factory import PaymentProviderFactory
from app.services.payment.providers.mock_provider import MockProvider
from app.db import models


class TestPaymentAgnosticBilling:
    """Test payment-agnostic billing functionality"""

    def setup_method(self):
        """Setup test environment"""
        # Clear any cached provider instances
        PaymentProviderFactory.clear_instances()

        # Create mock database session
        self.mock_db = Mock(spec=Session)

        # Create mock org
        self.org_id = "test-org-123"
        self.mock_org = models.Org(id=self.org_id, name="Test Org")

    @pytest.mark.asyncio
    async def test_create_customer_with_mock_provider(self):
        """Test creating a customer using mock provider"""
        # Arrange
        mock_provider = MockProvider()
        billing_service = BillingService(self.mock_db, mock_provider)

        # Mock database operations
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            self.mock_org
        )
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        self.mock_db.refresh = Mock()

        # Act
        billing_customer = await billing_service.create_customer_for_org(
            org_id=self.org_id, email="test@example.com", name="Test Customer"
        )

        # Assert
        assert billing_customer.org_id == self.org_id
        assert billing_customer.provider == "mock"
        assert billing_customer.email == "test@example.com"
        assert billing_customer.name == "Test Customer"

        # Verify database operations
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_checkout_session_with_mock_provider(self):
        """Test creating checkout session using mock provider"""
        # Arrange
        mock_provider = MockProvider()
        billing_service = BillingService(self.mock_db, mock_provider)

        # Create a mock billing customer
        mock_billing_customer = models.BillingCustomer(
            id="billing-customer-123",
            org_id=self.org_id,
            provider="mock",
            external_customer_id="mock_cus_123",
            email="test@example.com",
        )

        # Mock database operations
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_billing_customer
        )

        # Ensure provider has the customer registered
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        from app.services.payment.protocol import Customer

        mock_provider._customers[mock_billing_customer.external_customer_id] = Customer(
            id=mock_billing_customer.external_customer_id,
            email=mock_billing_customer.email,
            name="Test",
            metadata={"org_id": self.org_id},
        )

        # Act
        checkout_session = await billing_service.create_checkout_session(
            org_id=self.org_id,
            plan_id="test-plan-123",
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
        )

        # Assert
        assert checkout_session.customer_id == "mock_cus_123"
        assert "mock-checkout.example.com" in checkout_session.url
        assert checkout_session.id.startswith("mock_cs_")

    @pytest.mark.asyncio
    async def test_provider_switching(self):
        """Test that switching providers doesn't break business logic"""
        # Test with Mock provider
        mock_provider = MockProvider()
        billing_service_mock = BillingService(self.mock_db, mock_provider)

        # Create customer with mock provider
        customer_mock = await mock_provider.create_customer(
            email="test@example.com", name="Test Customer"
        )

        assert customer_mock.id.startswith("mock_cus_")
        assert mock_provider.get_provider_name() == "mock"

        # Test with different provider (simulated)
        # In real scenario, this would be StripeProvider, PayPalProvider, etc.
        class FakeProvider(MockProvider):
            def get_provider_name(self) -> str:
                return "fake"

            async def create_customer(self, email: str, name=None, metadata=None):
                customer = await super().create_customer(email, name, metadata)
                customer.id = f"fake_cus_{customer.id.split('_')[-1]}"
                return customer

        fake_provider = FakeProvider()
        billing_service_fake = BillingService(self.mock_db, fake_provider)

        customer_fake = await fake_provider.create_customer(
            email="test@example.com", name="Test Customer"
        )

        assert customer_fake.id.startswith("fake_cus_")
        assert fake_provider.get_provider_name() == "fake"

        # Both services use the same interface
        assert hasattr(billing_service_mock, "create_customer_for_org")
        assert hasattr(billing_service_fake, "create_customer_for_org")

    def test_payment_provider_factory(self):
        """Test payment provider factory functionality"""
        # Test available providers
        available = PaymentProviderFactory.get_available_providers()
        assert "mock" in available

        # Test creating mock provider
        provider = PaymentProviderFactory.create_provider("mock")
        assert isinstance(provider, MockProvider)
        assert provider.get_provider_name() == "mock"

        # Test singleton behavior
        provider2 = PaymentProviderFactory.create_provider("mock")
        assert provider is provider2  # Same instance

        # Test invalid provider
        with pytest.raises(Exception):
            PaymentProviderFactory.create_provider("nonexistent")

    @pytest.mark.asyncio
    async def test_webhook_handling_provider_agnostic(self):
        """Test webhook handling works with any provider"""
        # Arrange
        mock_provider = MockProvider()
        billing_service = BillingService(self.mock_db, mock_provider)

        # Mock database operations for event logging
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()

        # Create test webhook payload
        import json

        webhook_payload = json.dumps(
            {
                "type": "customer.subscription.created",
                "data": {
                    "object": {
                        "id": "sub_123",
                        "customer": "cus_123",
                        "status": "active",
                        "metadata": {"org_id": self.org_id},
                    }
                },
            }
        ).encode()

        # Act
        success = await billing_service.handle_webhook_event(
            payload=webhook_payload, signature="mock_signature"
        )

        # Assert
        assert success is True
        self.mock_db.add.assert_called()  # Event was logged
        self.mock_db.commit.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
