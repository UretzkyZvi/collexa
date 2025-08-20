"""
Billing orchestrator service.

This service coordinates complex billing workflows by orchestrating
multiple smaller billing services.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.billing.customer_service import CustomerService
from app.services.billing.subscription_service import SubscriptionService
from app.services.billing.checkout_service import CheckoutService
from app.services.billing.webhook_service import WebhookService
from app.services.payment.factory import get_payment_provider
from app.services.payment.protocol import PaymentProvider, CheckoutSession
from app.db import models
import logging

logger = logging.getLogger(__name__)


class BillingOrchestrator:
    """
    Orchestrator for complex billing workflows.
    
    This service coordinates multiple billing services to handle
    complex operations like subscription setup, plan changes, etc.
    """
    
    def __init__(self, db: Session, payment_provider: Optional[PaymentProvider] = None):
        self.db = db
        self.payment_provider = payment_provider or get_payment_provider()
        
        # Initialize component services
        self.customer_service = CustomerService(db, self.payment_provider)
        self.subscription_service = SubscriptionService(db, self.payment_provider)
        self.checkout_service = CheckoutService(db, self.payment_provider)
        self.webhook_service = WebhookService(db, self.payment_provider)
    
    async def setup_organization_billing(
        self,
        org_id: str,
        email: str,
        name: Optional[str] = None
    ) -> models.BillingCustomer:
        """
        Set up billing for a new organization.
        
        Args:
            org_id: Organization ID
            email: Billing email
            name: Organization name
            
        Returns:
            Created BillingCustomer
        """
        logger.info(f"Setting up billing for organization {org_id}")
        
        # Create billing customer
        billing_customer = await self.customer_service.create_customer_for_org(
            org_id=org_id,
            email=email,
            name=name
        )
        
        logger.info(f"Billing setup complete for organization {org_id}")
        return billing_customer
    
    async def create_subscription_checkout(
        self,
        org_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        trial_days: Optional[int] = None
    ) -> CheckoutSession:
        """
        Create a checkout session for subscription signup.
        
        Args:
            org_id: Organization ID
            plan_id: Plan ID to subscribe to
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            trial_days: Optional trial period
            
        Returns:
            CheckoutSession for payment
        """
        logger.info(f"Creating subscription checkout for org {org_id}, plan {plan_id}")
        
        # Prepare metadata
        metadata = {
            "org_id": org_id,
            "plan_id": plan_id
        }
        
        if trial_days:
            metadata["trial_days"] = trial_days
        
        # Create checkout session
        if trial_days:
            checkout_session = await self.checkout_service.create_trial_checkout(
                org_id=org_id,
                plan_id=plan_id,
                trial_days=trial_days,
                success_url=success_url,
                cancel_url=cancel_url
            )
        else:
            checkout_session = await self.checkout_service.create_checkout_session(
                org_id=org_id,
                plan_id=plan_id,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata
            )
        
        logger.info(f"Created checkout session {checkout_session.id} for org {org_id}")
        return checkout_session
    
    async def change_subscription_plan(
        self,
        org_id: str,
        new_plan_id: str,
        success_url: str,
        cancel_url: str
    ) -> CheckoutSession:
        """
        Create checkout for plan change.
        
        Args:
            org_id: Organization ID
            new_plan_id: New plan ID
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            
        Returns:
            CheckoutSession for plan change
        """
        logger.info(f"Creating plan change checkout for org {org_id} to plan {new_plan_id}")
        
        # Get current subscription
        current_subscription = await self.subscription_service.get_subscription_for_org(org_id)
        if not current_subscription:
            raise ValueError(f"No active subscription found for org {org_id}")
        
        # Create plan change checkout
        checkout_session = await self.checkout_service.create_plan_change_checkout(
            org_id=org_id,
            new_plan_id=new_plan_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        logger.info(f"Created plan change checkout {checkout_session.id} for org {org_id}")
        return checkout_session
    
    async def cancel_organization_subscription(self, org_id: str) -> bool:
        """
        Cancel subscription for an organization.
        
        Args:
            org_id: Organization ID
            
        Returns:
            True if subscription was canceled
        """
        logger.info(f"Canceling subscription for org {org_id}")
        
        success = await self.subscription_service.cancel_subscription_for_org(org_id)
        
        if success:
            logger.info(f"Successfully canceled subscription for org {org_id}")
        else:
            logger.warning(f"No subscription found to cancel for org {org_id}")
        
        return success
    
    async def process_webhook_event(self, payload: bytes, signature: str) -> bool:
        """
        Process webhook event from payment provider.
        
        Args:
            payload: Raw webhook payload
            signature: Webhook signature
            
        Returns:
            True if event was processed successfully
        """
        return await self.webhook_service.process_webhook(payload, signature)
    
    async def get_organization_billing_status(self, org_id: str) -> Dict[str, Any]:
        """
        Get comprehensive billing status for an organization.
        
        Args:
            org_id: Organization ID
            
        Returns:
            Dictionary with billing status information
        """
        # Get billing customer
        billing_customer = await self.customer_service.get_customer_by_org(org_id)
        if not billing_customer:
            return {
                "has_billing": False,
                "customer": None,
                "subscription": None,
                "provider": None
            }
        
        # Get subscription
        subscription = await self.subscription_service.get_subscription_for_org(org_id)
        
        # Get provider dashboard URL
        dashboard_url = self.customer_service.get_provider_dashboard_url(billing_customer.id)
        
        return {
            "has_billing": True,
            "customer": {
                "id": billing_customer.id,
                "email": billing_customer.email,
                "name": billing_customer.name,
                "provider": billing_customer.provider,
                "external_customer_id": billing_customer.external_customer_id,
                "dashboard_url": dashboard_url
            },
            "subscription": {
                "id": subscription.id,
                "status": subscription.status,
                "plan_id": subscription.plan_id,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "external_subscription_id": subscription.external_subscription_id
            } if subscription else None,
            "provider": billing_customer.provider
        }
    
    async def update_organization_billing_info(
        self,
        org_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None
    ) -> Optional[models.BillingCustomer]:
        """
        Update billing information for an organization.
        
        Args:
            org_id: Organization ID
            email: New email (optional)
            name: New name (optional)
            
        Returns:
            Updated BillingCustomer or None if not found
        """
        billing_customer = await self.customer_service.get_customer_by_org(org_id)
        if not billing_customer:
            return None
        
        return await self.customer_service.update_customer(
            customer_id=billing_customer.id,
            email=email,
            name=name
        )
    
    def get_provider_name(self) -> str:
        """Get the name of the current payment provider"""
        return self.payment_provider.get_provider_name()
    
    def is_provider_configured(self) -> bool:
        """Check if the payment provider is properly configured"""
        try:
            # Try to get provider name - this will fail if not configured
            provider_name = self.payment_provider.get_provider_name()
            return bool(provider_name)
        except Exception:
            return False
