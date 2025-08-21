"""
Billing service that provides payment-agnostic billing operations.

This service acts as a bridge between the application's business logic
and the payment provider, handling data persistence and provider interactions.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.services.payment.factory import get_payment_provider
from app.services.payment.protocol import (
    PaymentProvider,
    CheckoutSession,
    WebhookEvent,
    PaymentProviderError,
)
from app.db import models
from app.core.config import settings
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class BillingService:
    """
    Payment-agnostic billing service.

    This service handles all billing operations while abstracting away
    the specific payment provider implementation.
    """

    def __init__(self, db: Session, payment_provider: Optional[PaymentProvider] = None):
        self.db = db
        self.payment_provider = payment_provider or get_payment_provider()

    async def create_customer_for_org(
        self, org_id: str, email: str, name: Optional[str] = None
    ) -> models.BillingCustomer:
        """
        Create a billing customer for an organization.

        Args:
            org_id: Organization ID
            email: Customer email
            name: Customer name (optional)

        Returns:
            BillingCustomer model instance
        """
        try:
            # Create customer with payment provider
            provider_customer = await self.payment_provider.create_customer(
                email=email, name=name, metadata={"org_id": org_id}
            )

            # Create internal billing customer record
            billing_customer = models.BillingCustomer(
                id=str(uuid.uuid4()),
                org_id=org_id,
                provider=self.payment_provider.get_provider_name(),
                external_customer_id=provider_customer.id,
                email=email,
                name=name,
                metadata_json=provider_customer.metadata,
            )

            self.db.add(billing_customer)
            self.db.commit()
            self.db.refresh(billing_customer)

            # Update org with customer reference (for backward compatibility)
            org = self.db.query(models.Org).filter(models.Org.id == org_id).first()
            if org:
                # Store provider-specific customer ID in org for backward compatibility
                if self.payment_provider.get_provider_name() == "stripe":
                    # Back-compat placeholder: store stripe customer on org if field
                    # exists
                    try:
                        org.stripe_customer_id = provider_customer.id
                    except Exception:
                        pass
                self.db.commit()

            logger.info(
                f"Created billing customer for org {org_id} with provider {self.payment_provider.get_provider_name()}"
            )
            return billing_customer

        except PaymentProviderError as e:
            logger.error(f"Failed to create customer for org {org_id}: {e}")
            self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating customer for org {org_id}: {e}")
            self.db.rollback()
            raise

    async def get_customer_by_org(
        self, org_id: str
    ) -> Optional[models.BillingCustomer]:
        """Get billing customer for an organization"""
        return (
            self.db.query(models.BillingCustomer)
            .filter(models.BillingCustomer.org_id == org_id)
            .first()
        )

    async def create_checkout_session(
        self, org_id: str, plan_id: str, success_url: str, cancel_url: str
    ) -> CheckoutSession:
        """
        Create a checkout session for subscription signup.

        Args:
            org_id: Organization ID
            plan_id: Plan/price ID from payment provider
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel

        Returns:
            CheckoutSession with URL for customer to complete payment
        """
        # Get or create billing customer
        billing_customer = await self.get_customer_by_org(org_id)
        if not billing_customer:
            # Get org details to create customer
            org = self.db.query(models.Org).filter(models.Org.id == org_id).first()
            if not org:
                raise ValueError(f"Organization {org_id} not found")

            # Create customer (using org name as customer name for now)
            billing_customer = await self.create_customer_for_org(
                org_id=org_id,
                email=f"billing@{org.name.lower().replace(' ', '')}.com",  # Placeholder
                name=org.name,
            )

        try:
            checkout_session = await self.payment_provider.create_checkout_session(
                customer_id=billing_customer.external_customer_id,
                plan_id=plan_id,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"org_id": org_id},
            )

            logger.info(f"Created checkout session for org {org_id}")
            return checkout_session

        except PaymentProviderError as e:
            logger.error(f"Failed to create checkout session for org {org_id}: {e}")
            raise

    async def handle_webhook_event(self, payload: bytes, signature: str) -> bool:
        """
        Handle webhook event from payment provider.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature for verification

        Returns:
            True if event was processed successfully
        """
        try:
            # Verify and parse webhook event
            event = self.payment_provider.verify_webhook_signature(
                payload=payload,
                signature=signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,  # TODO: Make this provider-agnostic
            )

            # Log the event
            await self._log_billing_event(event)

            # Process event based on type
            if event.type.startswith("customer.subscription."):
                await self._handle_subscription_event(event)
            elif event.type.startswith("invoice."):
                await self._handle_invoice_event(event)
            elif event.type.startswith("customer."):
                await self._handle_customer_event(event)

            logger.info(f"Processed webhook event {event.id} of type {event.type}")
            return True

        except Exception as e:
            logger.error(f"Failed to process webhook event: {e}")
            return False

    async def get_subscription_for_org(
        self, org_id: str
    ) -> Optional[models.BillingSubscription]:
        """Get active subscription for an organization"""
        billing_customer = await self.get_customer_by_org(org_id)
        if not billing_customer:
            return None

        return (
            self.db.query(models.BillingSubscription)
            .filter(
                and_(
                    models.BillingSubscription.customer_id == billing_customer.id,
                    models.BillingSubscription.status.in_(["active", "trialing"]),
                )
            )
            .first()
        )

    async def cancel_subscription_for_org(self, org_id: str) -> bool:
        """Cancel subscription for an organization"""
        subscription = await self.get_subscription_for_org(org_id)
        if not subscription:
            return False

        try:
            # Cancel with payment provider
            await self.payment_provider.cancel_subscription(
                subscription.external_subscription_id
            )

            # Update local record
            subscription.status = "canceled"
            subscription.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Canceled subscription for org {org_id}")
            return True

        except PaymentProviderError as e:
            logger.error(f"Failed to cancel subscription for org {org_id}: {e}")
            self.db.rollback()
            raise

    async def record_usage(self, org_id: str, quantity: int) -> bool:
        """Record usage for metered billing"""
        subscription = await self.get_subscription_for_org(org_id)
        if not subscription:
            logger.warning(f"No active subscription found for org {org_id}")
            return False

        try:
            # TODO: Get subscription item ID for metered billing
            # This would need to be stored in the subscription record
            subscription_item_id = (subscription.metadata_json or {}).get(
                "metered_item_id"
            )

            if not subscription_item_id:
                logger.warning(f"No metered item ID found for org {org_id}")
                return False

            await self.payment_provider.create_usage_record(
                subscription_item_id=subscription_item_id, quantity=quantity
            )

            logger.info(f"Recorded usage {quantity} for org {org_id}")
            return True

        except PaymentProviderError as e:
            logger.error(f"Failed to record usage for org {org_id}: {e}")
            return False

    # Private helper methods

    async def _log_billing_event(self, event: WebhookEvent):
        """Log billing event to database"""
        # Extract org_id from event metadata
        org_id = None
        if event.data.get("object", {}).get("metadata"):
            org_id = event.data["object"]["metadata"].get("org_id")

        billing_event = models.BillingEvent(
            id=str(uuid.uuid4()),
            org_id=org_id,
            event_type=event.type,
            provider=event.provider,
            external_event_id=event.id,
            metadata_json=event.data,
            processed_at=datetime.utcnow(),
        )

        self.db.add(billing_event)
        self.db.commit()

    async def _handle_subscription_event(self, event: WebhookEvent):
        """Handle subscription-related webhook events"""
        subscription_data = event.data.get("object", {})
        customer_id = subscription_data.get("customer")

        if not customer_id:
            logger.warning(f"No customer ID in subscription event {event.id}")
            return

        # Find billing customer
        billing_customer = (
            self.db.query(models.BillingCustomer)
            .filter(models.BillingCustomer.external_customer_id == customer_id)
            .first()
        )

        if not billing_customer:
            logger.warning(f"Billing customer not found for external ID {customer_id}")
            return

        # Handle different subscription events
        if event.type == "customer.subscription.created":
            await self._create_or_update_subscription(
                billing_customer, subscription_data
            )
        elif event.type == "customer.subscription.updated":
            await self._create_or_update_subscription(
                billing_customer, subscription_data
            )
        elif event.type == "customer.subscription.deleted":
            await self._cancel_subscription(billing_customer, subscription_data)

    async def _create_or_update_subscription(
        self,
        billing_customer: models.BillingCustomer,
        subscription_data: Dict[str, Any],
    ):
        """Create or update subscription record"""
        subscription_id = subscription_data.get("id")

        # Check if subscription already exists
        existing = (
            self.db.query(models.BillingSubscription)
            .filter(
                models.BillingSubscription.external_subscription_id == subscription_id
            )
            .first()
        )

        if existing:
            # Update existing subscription
            existing.status = subscription_data.get("status", "active")
            existing.current_period_start = datetime.fromtimestamp(
                subscription_data.get("current_period_start", 0)
            )
            existing.current_period_end = datetime.fromtimestamp(
                subscription_data.get("current_period_end", 0)
            )
            existing.metadata_json = subscription_data.get("metadata", {})
            existing.updated_at = datetime.utcnow()
        else:
            # Create new subscription
            subscription = models.BillingSubscription(
                id=str(uuid.uuid4()),
                customer_id=billing_customer.id,
                external_subscription_id=subscription_id,
                plan_id=subscription_data.get("items", {})
                .get("data", [{}])[0]
                .get("price", {})
                .get("id", ""),
                status=subscription_data.get("status", "active"),
                current_period_start=datetime.fromtimestamp(
                    subscription_data.get("current_period_start", 0)
                ),
                current_period_end=datetime.fromtimestamp(
                    subscription_data.get("current_period_end", 0)
                ),
                metadata_json=subscription_data.get("metadata", {}),
            )
            self.db.add(subscription)

        self.db.commit()

    async def _cancel_subscription(
        self,
        billing_customer: models.BillingCustomer,
        subscription_data: Dict[str, Any],
    ):
        """Cancel subscription record"""
        subscription_id = subscription_data.get("id")

        subscription = (
            self.db.query(models.BillingSubscription)
            .filter(
                models.BillingSubscription.external_subscription_id == subscription_id
            )
            .first()
        )

        if subscription:
            subscription.status = "canceled"
            subscription.updated_at = datetime.utcnow()
            self.db.commit()

    async def _handle_invoice_event(self, event: WebhookEvent):
        """Handle invoice-related webhook events"""
        # TODO: Implement invoice event handling
        logger.info(f"Invoice event {event.type} received but not yet implemented")

    async def _handle_customer_event(self, event: WebhookEvent):
        """Handle customer-related webhook events"""
        # TODO: Implement customer event handling
        logger.info(f"Customer event {event.type} received but not yet implemented")
