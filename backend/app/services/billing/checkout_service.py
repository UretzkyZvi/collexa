"""
Checkout session management service.

This service handles checkout session creation and management
for subscription signups and plan changes.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.services.payment.factory import get_payment_provider
from app.services.payment.protocol import PaymentProvider, CheckoutSession, PaymentProviderError
from app.services.billing.customer_service import CustomerService
import logging

logger = logging.getLogger(__name__)


class CheckoutService:
    """Service for managing checkout sessions"""
    
    def __init__(self, db: Session, payment_provider: Optional[PaymentProvider] = None):
        self.db = db
        self.payment_provider = payment_provider or get_payment_provider()
        self.customer_service = CustomerService(db, payment_provider)
    
    async def create_checkout_session(
        self,
        org_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CheckoutSession:
        """
        Create a checkout session for subscription signup.
        
        Args:
            org_id: Organization ID
            plan_id: Plan/price ID from payment provider
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            metadata: Optional metadata to include
            
        Returns:
            CheckoutSession with URL for customer to complete payment
        """
        try:
            # Get or create billing customer
            billing_customer = await self.customer_service.get_or_create_customer_for_org(org_id)
            
            # Prepare metadata
            session_metadata = {
                "org_id": org_id,
                **(metadata or {})
            }
            
            # Create checkout session with payment provider
            checkout_session = await self.payment_provider.create_checkout_session(
                customer_id=billing_customer.external_customer_id,
                plan_id=plan_id,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=session_metadata
            )
            
            logger.info(f"Created checkout session for org {org_id}: {checkout_session.id}")
            return checkout_session
            
        except PaymentProviderError as e:
            logger.error(f"Failed to create checkout session for org {org_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session for org {org_id}: {e}")
            raise
    
    async def create_plan_change_checkout(
        self,
        org_id: str,
        new_plan_id: str,
        success_url: str,
        cancel_url: str
    ) -> CheckoutSession:
        """
        Create checkout session for plan changes.
        
        Args:
            org_id: Organization ID
            new_plan_id: New plan ID to switch to
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            
        Returns:
            CheckoutSession for plan change
        """
        return await self.create_checkout_session(
            org_id=org_id,
            plan_id=new_plan_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "type": "plan_change",
                "new_plan_id": new_plan_id
            }
        )
    
    async def create_trial_checkout(
        self,
        org_id: str,
        plan_id: str,
        trial_days: int,
        success_url: str,
        cancel_url: str
    ) -> CheckoutSession:
        """
        Create checkout session with trial period.
        
        Args:
            org_id: Organization ID
            plan_id: Plan ID for after trial
            trial_days: Number of trial days
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            
        Returns:
            CheckoutSession with trial configuration
        """
        return await self.create_checkout_session(
            org_id=org_id,
            plan_id=plan_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "type": "trial",
                "trial_days": trial_days
            }
        )
    
    def get_checkout_success_data(self, checkout_session_id: str) -> Dict[str, Any]:
        """
        Get data to display on checkout success page.
        
        Args:
            checkout_session_id: Checkout session ID
            
        Returns:
            Dictionary with success page data
        """
        # In a real implementation, you might want to store checkout session
        # data in the database and retrieve it here
        return {
            "session_id": checkout_session_id,
            "message": "Subscription activated successfully!",
            "next_steps": [
                "Your subscription is now active",
                "You can start using all premium features",
                "Check your email for the receipt"
            ]
        }
    
    def get_checkout_cancel_data(self, checkout_session_id: str) -> Dict[str, Any]:
        """
        Get data to display on checkout cancel page.
        
        Args:
            checkout_session_id: Checkout session ID
            
        Returns:
            Dictionary with cancel page data
        """
        return {
            "session_id": checkout_session_id,
            "message": "Checkout was canceled",
            "next_steps": [
                "No charges were made",
                "You can try again anytime",
                "Contact support if you need help"
            ]
        }
