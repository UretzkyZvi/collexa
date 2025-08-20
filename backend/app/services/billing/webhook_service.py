"""
Webhook processing service.

This service handles webhook events from payment providers,
processing subscription lifecycle events and other billing updates.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.payment.factory import get_payment_provider
from app.services.payment.protocol import PaymentProvider, WebhookEvent, WebhookVerificationError
from app.services.billing.customer_service import CustomerService
from app.services.billing.subscription_service import SubscriptionService
from app.db import models
from app.core.config import settings
import logging
import uuid

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing payment provider webhooks"""
    
    def __init__(self, db: Session, payment_provider: PaymentProvider = None):
        self.db = db
        self.payment_provider = payment_provider or get_payment_provider()
        self.customer_service = CustomerService(db, payment_provider)
        self.subscription_service = SubscriptionService(db, payment_provider)
    
    async def process_webhook(self, payload: bytes, signature: str, secret: str = None) -> bool:
        """
        Process webhook event from payment provider.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature for verification
            secret: Webhook secret (uses default if not provided)
            
        Returns:
            True if event was processed successfully
        """
        try:
            # Verify and parse webhook event
            webhook_secret = secret or self._get_webhook_secret()
            event = self.payment_provider.verify_webhook_signature(
                payload=payload,
                signature=signature,
                secret=webhook_secret
            )
            
            # Log the event
            await self._log_billing_event(event)
            
            # Process event based on type
            success = await self._process_event(event)
            
            if success:
                logger.info(f"Successfully processed webhook event {event.id} of type {event.type}")
            else:
                logger.warning(f"Failed to process webhook event {event.id} of type {event.type}")
            
            return success
            
        except WebhookVerificationError as e:
            logger.error(f"Webhook verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to process webhook event: {e}")
            return False
    
    async def _process_event(self, event: WebhookEvent) -> bool:
        """Process a verified webhook event"""
        try:
            if event.type.startswith("customer.subscription."):
                return await self._handle_subscription_event(event)
            elif event.type.startswith("invoice."):
                return await self._handle_invoice_event(event)
            elif event.type.startswith("customer."):
                return await self._handle_customer_event(event)
            elif event.type.startswith("checkout.session."):
                return await self._handle_checkout_event(event)
            else:
                logger.info(f"Unhandled event type: {event.type}")
                return True  # Don't fail for unknown events
                
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}")
            return False
    
    async def _handle_subscription_event(self, event: WebhookEvent) -> bool:
        """Handle subscription-related webhook events"""
        subscription_data = event.data.get("object", {})
        customer_id = subscription_data.get("customer")
        
        if not customer_id:
            logger.warning(f"No customer ID in subscription event {event.id}")
            return False
        
        # Find billing customer
        billing_customer = await self.customer_service.get_customer_by_external_id(customer_id)
        if not billing_customer:
            logger.warning(f"Billing customer not found for external ID {customer_id}")
            return False
        
        # Handle different subscription events
        if event.type == "customer.subscription.created":
            await self.subscription_service.create_or_update_subscription(
                billing_customer.id, subscription_data
            )
        elif event.type == "customer.subscription.updated":
            await self.subscription_service.create_or_update_subscription(
                billing_customer.id, subscription_data
            )
        elif event.type == "customer.subscription.deleted":
            await self.subscription_service.update_subscription_status(
                subscription_data.get("id"), "canceled"
            )
        elif event.type == "customer.subscription.trial_will_end":
            # Handle trial ending notification
            logger.info(f"Trial ending for subscription {subscription_data.get('id')}")
        
        return True
    
    async def _handle_invoice_event(self, event: WebhookEvent) -> bool:
        """Handle invoice-related webhook events"""
        invoice_data = event.data.get("object", {})
        
        if event.type == "invoice.payment_succeeded":
            logger.info(f"Payment succeeded for invoice {invoice_data.get('id')}")
            # Could update subscription status, send confirmation emails, etc.
        elif event.type == "invoice.payment_failed":
            logger.warning(f"Payment failed for invoice {invoice_data.get('id')}")
            # Could update subscription status, send dunning emails, etc.
        elif event.type == "invoice.created":
            logger.info(f"Invoice created: {invoice_data.get('id')}")
        
        return True
    
    async def _handle_customer_event(self, event: WebhookEvent) -> bool:
        """Handle customer-related webhook events"""
        customer_data = event.data.get("object", {})
        
        if event.type == "customer.updated":
            # Update local customer record if needed
            billing_customer = await self.customer_service.get_customer_by_external_id(
                customer_data.get("id")
            )
            if billing_customer:
                billing_customer.email = customer_data.get("email", billing_customer.email)
                billing_customer.name = customer_data.get("name", billing_customer.name)
                billing_customer.metadata = customer_data.get("metadata", billing_customer.metadata)
                self.db.commit()
        elif event.type == "customer.deleted":
            logger.info(f"Customer deleted: {customer_data.get('id')}")
        
        return True
    
    async def _handle_checkout_event(self, event: WebhookEvent) -> bool:
        """Handle checkout session events"""
        session_data = event.data.get("object", {})
        
        if event.type == "checkout.session.completed":
            logger.info(f"Checkout session completed: {session_data.get('id')}")
            # The subscription.created event will handle the actual subscription setup
        elif event.type == "checkout.session.expired":
            logger.info(f"Checkout session expired: {session_data.get('id')}")
        
        return True
    
    async def _log_billing_event(self, event: WebhookEvent):
        """Log billing event to database"""
        # Extract org_id from event metadata
        org_id = None
        event_data = event.data.get("object", {})
        if event_data.get("metadata"):
            org_id = event_data["metadata"].get("org_id")
        
        # Try to get org_id from customer if not in metadata
        if not org_id and event_data.get("customer"):
            billing_customer = await self.customer_service.get_customer_by_external_id(
                event_data["customer"]
            )
            if billing_customer:
                org_id = billing_customer.org_id
        
        billing_event = models.BillingEvent(
            id=str(uuid.uuid4()),
            org_id=org_id,
            event_type=event.type,
            provider=event.provider,
            external_event_id=event.id,
            amount_cents=self._extract_amount_cents(event_data),
            metadata=event.data,
            processed_at=datetime.utcnow()
        )
        
        self.db.add(billing_event)
        self.db.commit()
    
    def _extract_amount_cents(self, event_data: Dict[str, Any]) -> int:
        """Extract amount in cents from event data"""
        # Different event types have amounts in different places
        amount_cents = 0
        
        # Try common amount fields
        for field in ["amount_total", "amount_due", "amount_paid", "total"]:
            if field in event_data:
                amount_cents = event_data[field]
                break
        
        return amount_cents or 0
    
    def _get_webhook_secret(self) -> str:
        """Get webhook secret for the current provider"""
        provider_name = self.payment_provider.get_provider_name()
        
        if provider_name == "stripe":
            return settings.STRIPE_WEBHOOK_SECRET
        elif provider_name == "paypal":
            return settings.PAYPAL_WEBHOOK_ID
        elif provider_name == "square":
            return settings.SQUARE_WEBHOOK_SIGNATURE_KEY
        else:
            return ""  # Mock provider doesn't need a secret
