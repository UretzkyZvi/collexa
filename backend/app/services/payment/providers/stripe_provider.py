"""
Stripe payment provider implementation.

This module implements the PaymentProvider interface for Stripe,
handling all Stripe-specific API interactions and data transformations.
"""

import stripe
from typing import Dict, Any, Optional, List
from app.services.payment.protocol import (
    PaymentProvider, Customer, PaymentMethod, Subscription, Invoice, 
    CheckoutSession, WebhookEvent, PaymentStatus, SubscriptionStatus,
    PaymentProviderError, CustomerNotFoundError, SubscriptionNotFoundError,
    WebhookVerificationError, PaymentProviderConfigError
)
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class StripeProvider(PaymentProvider):
    """Stripe implementation of the PaymentProvider interface"""
    
    def __init__(self):
        if not settings.STRIPE_SECRET_KEY:
            raise PaymentProviderConfigError(
                "STRIPE_SECRET_KEY is required", 
                "stripe"
            )
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self._webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    async def create_customer(
        self, 
        email: str, 
        name: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Customer:
        """Create a new Stripe customer"""
        try:
            stripe_customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            return self._convert_stripe_customer(stripe_customer)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise PaymentProviderError(
                f"Failed to create customer: {str(e)}", 
                "stripe", 
                e
            )
    
    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get Stripe customer by ID"""
        try:
            stripe_customer = stripe.Customer.retrieve(customer_id)
            if stripe_customer.deleted:
                return None
            return self._convert_stripe_customer(stripe_customer)
        except stripe.error.InvalidRequestError:
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get Stripe customer {customer_id}: {e}")
            raise PaymentProviderError(
                f"Failed to get customer: {str(e)}", 
                "stripe", 
                e
            )
    
    async def update_customer(
        self, 
        customer_id: str, 
        email: Optional[str] = None,
        name: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Customer:
        """Update Stripe customer"""
        try:
            update_data = {}
            if email is not None:
                update_data['email'] = email
            if name is not None:
                update_data['name'] = name
            if metadata is not None:
                update_data['metadata'] = metadata
            
            stripe_customer = stripe.Customer.modify(customer_id, **update_data)
            return self._convert_stripe_customer(stripe_customer)
        except stripe.error.InvalidRequestError as e:
            raise CustomerNotFoundError(
                f"Customer {customer_id} not found", 
                "stripe", 
                e
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe customer {customer_id}: {e}")
            raise PaymentProviderError(
                f"Failed to update customer: {str(e)}", 
                "stripe", 
                e
            )
    
    async def create_checkout_session(
        self, 
        customer_id: str, 
        plan_id: str,
        success_url: str, 
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CheckoutSession:
        """Create Stripe checkout session"""
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {}
            )
            
            return CheckoutSession(
                id=session.id,
                url=session.url,
                customer_id=customer_id,
                metadata=session.metadata
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe checkout session: {e}")
            raise PaymentProviderError(
                f"Failed to create checkout session: {str(e)}", 
                "stripe", 
                e
            )
    
    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get Stripe subscription by ID"""
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            return self._convert_stripe_subscription(stripe_sub)
        except stripe.error.InvalidRequestError:
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get Stripe subscription {subscription_id}: {e}")
            raise PaymentProviderError(
                f"Failed to get subscription: {str(e)}", 
                "stripe", 
                e
            )
    
    async def cancel_subscription(self, subscription_id: str) -> Subscription:
        """Cancel Stripe subscription"""
        try:
            stripe_sub = stripe.Subscription.delete(subscription_id)
            return self._convert_stripe_subscription(stripe_sub)
        except stripe.error.InvalidRequestError as e:
            raise SubscriptionNotFoundError(
                f"Subscription {subscription_id} not found", 
                "stripe", 
                e
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel Stripe subscription {subscription_id}: {e}")
            raise PaymentProviderError(
                f"Failed to cancel subscription: {str(e)}", 
                "stripe", 
                e
            )
    
    async def create_usage_record(
        self, 
        subscription_item_id: str, 
        quantity: int, 
        timestamp: Optional[int] = None
    ) -> bool:
        """Create Stripe usage record for metered billing"""
        try:
            usage_record_data = {
                'quantity': quantity,
                'action': 'increment'
            }
            if timestamp:
                usage_record_data['timestamp'] = timestamp
            
            stripe.UsageRecord.create(
                subscription_item=subscription_item_id,
                **usage_record_data
            )
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe usage record: {e}")
            raise PaymentProviderError(
                f"Failed to create usage record: {str(e)}", 
                "stripe", 
                e
            )
    
    async def get_invoices(
        self, 
        customer_id: str, 
        limit: int = 10
    ) -> List[Invoice]:
        """Get Stripe customer invoices"""
        try:
            stripe_invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            return [self._convert_stripe_invoice(inv) for inv in stripe_invoices.data]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get Stripe invoices for {customer_id}: {e}")
            raise PaymentProviderError(
                f"Failed to get invoices: {str(e)}", 
                "stripe", 
                e
            )
    
    def verify_webhook_signature(
        self, 
        payload: bytes, 
        signature: str, 
        secret: str
    ) -> WebhookEvent:
        """Verify Stripe webhook signature and parse event"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, secret or self._webhook_secret
            )
            
            return WebhookEvent(
                id=event['id'],
                type=event['type'],
                data=event['data'],
                created=event['created'],
                provider='stripe'
            )
        except ValueError as e:
            raise WebhookVerificationError(
                "Invalid payload", 
                "stripe", 
                e
            )
        except stripe.error.SignatureVerificationError as e:
            raise WebhookVerificationError(
                "Invalid signature", 
                "stripe", 
                e
            )
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "stripe"
    
    def get_dashboard_url(self, customer_id: str) -> Optional[str]:
        """Get Stripe customer dashboard URL"""
        return f"https://dashboard.stripe.com/customers/{customer_id}"
    
    # Helper methods for data conversion
    
    def _convert_stripe_customer(self, stripe_customer) -> Customer:
        """Convert Stripe customer to our Customer model"""
        return Customer(
            id=stripe_customer.id,
            email=stripe_customer.email,
            name=stripe_customer.name,
            metadata=dict(stripe_customer.metadata) if stripe_customer.metadata else None
        )
    
    def _convert_stripe_subscription(self, stripe_sub) -> Subscription:
        """Convert Stripe subscription to our Subscription model"""
        status_mapping = {
            'active': SubscriptionStatus.ACTIVE,
            'canceled': SubscriptionStatus.CANCELED,
            'past_due': SubscriptionStatus.PAST_DUE,
            'unpaid': SubscriptionStatus.UNPAID,
            'trialing': SubscriptionStatus.TRIALING,
        }
        
        return Subscription(
            id=stripe_sub.id,
            customer_id=stripe_sub.customer,
            status=status_mapping.get(stripe_sub.status, SubscriptionStatus.ACTIVE),
            current_period_start=stripe_sub.current_period_start,
            current_period_end=stripe_sub.current_period_end,
            plan_id=stripe_sub.items.data[0].price.id if stripe_sub.items.data else "",
            metadata=dict(stripe_sub.metadata) if stripe_sub.metadata else None
        )
    
    def _convert_stripe_invoice(self, stripe_invoice) -> Invoice:
        """Convert Stripe invoice to our Invoice model"""
        status_mapping = {
            'draft': PaymentStatus.PENDING,
            'open': PaymentStatus.PENDING,
            'paid': PaymentStatus.SUCCEEDED,
            'void': PaymentStatus.CANCELED,
            'uncollectible': PaymentStatus.FAILED,
        }
        
        return Invoice(
            id=stripe_invoice.id,
            customer_id=stripe_invoice.customer,
            amount_cents=stripe_invoice.amount_due,
            status=status_mapping.get(stripe_invoice.status, PaymentStatus.PENDING),
            due_date=stripe_invoice.due_date,
            paid_at=stripe_invoice.status_transitions.paid_at if stripe_invoice.status_transitions else None,
            metadata=dict(stripe_invoice.metadata) if stripe_invoice.metadata else None
        )
