"""
Mock payment provider for testing and development.

This provider simulates payment operations without making real API calls,
useful for testing the payment-agnostic architecture and development.
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from app.services.payment.protocol import (
    PaymentProvider,
    Customer,
    Subscription,
    Invoice,
    CheckoutSession,
    WebhookEvent,
    PaymentStatus,
    SubscriptionStatus,
    CustomerNotFoundError,
    SubscriptionNotFoundError,
    WebhookVerificationError,
)
import logging

logger = logging.getLogger(__name__)


class MockProvider(PaymentProvider):
    """Mock implementation of PaymentProvider for testing"""

    def __init__(self):
        # In-memory storage for mock data
        self._customers: Dict[str, Customer] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._invoices: Dict[str, List[Invoice]] = {}
        self._checkout_sessions: Dict[str, CheckoutSession] = {}

        logger.info("Initialized MockProvider")

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        """Create a mock customer"""
        customer_id = f"mock_cus_{uuid.uuid4().hex[:12]}"
        customer = Customer(
            id=customer_id, email=email, name=name, metadata=metadata or {}
        )

        self._customers[customer_id] = customer
        logger.info(f"Created mock customer: {customer_id}")
        return customer

    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get mock customer by ID"""
        return self._customers.get(customer_id)

    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        """Update mock customer"""
        customer = self._customers.get(customer_id)
        if not customer:
            raise CustomerNotFoundError(f"Customer {customer_id} not found", "mock")

        # Update fields
        if email is not None:
            customer.email = email
        if name is not None:
            customer.name = name
        if metadata is not None:
            customer.metadata = metadata

        logger.info(f"Updated mock customer: {customer_id}")
        return customer

    async def create_checkout_session(
        self,
        customer_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CheckoutSession:
        """Create mock checkout session"""
        if customer_id not in self._customers:
            raise CustomerNotFoundError(f"Customer {customer_id} not found", "mock")

        session_id = f"mock_cs_{uuid.uuid4().hex[:12]}"
        session = CheckoutSession(
            id=session_id,
            url=f"https://mock-checkout.example.com/session/{session_id}",
            customer_id=customer_id,
            metadata=metadata or {},
        )

        self._checkout_sessions[session_id] = session

        # Simulate successful subscription creation after checkout
        await self._simulate_subscription_creation(customer_id, plan_id, metadata)

        logger.info(f"Created mock checkout session: {session_id}")
        return session

    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get mock subscription by ID"""
        return self._subscriptions.get(subscription_id)

    async def cancel_subscription(self, subscription_id: str) -> Subscription:
        """Cancel mock subscription"""
        subscription = self._subscriptions.get(subscription_id)
        if not subscription:
            raise SubscriptionNotFoundError(
                f"Subscription {subscription_id} not found", "mock"
            )

        # Update status to canceled
        subscription.status = SubscriptionStatus.CANCELED
        logger.info(f"Canceled mock subscription: {subscription_id}")
        return subscription

    async def create_usage_record(
        self, subscription_item_id: str, quantity: int, timestamp: Optional[int] = None
    ) -> bool:
        """Create mock usage record"""
        logger.info(
            f"Created mock usage record: {quantity} units for {subscription_item_id}"
        )
        return True

    async def get_invoices(self, customer_id: str, limit: int = 10) -> List[Invoice]:
        """Get mock customer invoices"""
        customer_invoices = self._invoices.get(customer_id, [])
        return customer_invoices[:limit]

    def verify_webhook_signature(
        self, payload: bytes, signature: str, secret: str
    ) -> WebhookEvent:
        """Verify mock webhook signature (always succeeds)"""
        try:
            import json

            data = json.loads(payload.decode())

            return WebhookEvent(
                id=f"mock_evt_{uuid.uuid4().hex[:12]}",
                type=data.get("type", "test.event"),
                data=data.get("data", {}),
                created=int(time.time()),
                provider="mock",
            )
        except Exception as e:
            raise WebhookVerificationError("Invalid payload", "mock", e)

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "mock"

    def get_dashboard_url(self, customer_id: str) -> Optional[str]:
        """Get mock dashboard URL"""
        return f"https://mock-dashboard.example.com/customers/{customer_id}"

    # Helper methods for simulation

    async def _simulate_subscription_creation(
        self, customer_id: str, plan_id: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Simulate subscription creation after checkout"""
        subscription_id = f"mock_sub_{uuid.uuid4().hex[:12]}"
        now = int(time.time())

        subscription = Subscription(
            id=subscription_id,
            customer_id=customer_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now + (30 * 24 * 60 * 60),  # 30 days from now
            plan_id=plan_id,
            metadata=metadata or {},
        )

        self._subscriptions[subscription_id] = subscription

        # Create a mock invoice
        invoice = Invoice(
            id=f"mock_in_{uuid.uuid4().hex[:12]}",
            customer_id=customer_id,
            amount_cents=2999,  # $29.99
            status=PaymentStatus.SUCCEEDED,
            paid_at=now,
            metadata={"subscription_id": subscription_id},
        )

        if customer_id not in self._invoices:
            self._invoices[customer_id] = []
        self._invoices[customer_id].append(invoice)

        logger.info(f"Simulated subscription creation: {subscription_id}")

    def simulate_webhook_event(
        self, event_type: str, data: Dict[str, Any]
    ) -> WebhookEvent:
        """Simulate a webhook event (useful for testing)"""
        return WebhookEvent(
            id=f"mock_evt_{uuid.uuid4().hex[:12]}",
            type=event_type,
            data=data,
            created=int(time.time()),
            provider="mock",
        )

    def clear_all_data(self):
        """Clear all mock data (useful for testing)"""
        self._customers.clear()
        self._subscriptions.clear()
        self._invoices.clear()
        self._checkout_sessions.clear()
        logger.info("Cleared all mock data")

    def get_all_customers(self) -> List[Customer]:
        """Get all mock customers (useful for testing)"""
        return list(self._customers.values())

    def get_all_subscriptions(self) -> List[Subscription]:
        """Get all mock subscriptions (useful for testing)"""
        return list(self._subscriptions.values())
