"""
Subscription management service.

This service handles subscription lifecycle operations including
creation, updates, cancellation, and status tracking.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.services.payment.factory import get_payment_provider
from app.services.payment.protocol import PaymentProvider, PaymentProviderError
from app.db import models
import logging
import uuid

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscriptions"""
    
    def __init__(self, db: Session, payment_provider: Optional[PaymentProvider] = None):
        self.db = db
        self.payment_provider = payment_provider or get_payment_provider()
    
    async def get_subscription_for_org(self, org_id: str) -> Optional[models.BillingSubscription]:
        """Get active subscription for an organization"""
        # First get the billing customer
        billing_customer = self.db.query(models.BillingCustomer).filter(
            models.BillingCustomer.org_id == org_id
        ).first()
        
        if not billing_customer:
            return None
        
        return self.db.query(models.BillingSubscription).filter(
            and_(
                models.BillingSubscription.customer_id == billing_customer.id,
                models.BillingSubscription.status.in_(["active", "trialing"])
            )
        ).first()
    
    async def get_subscription_by_id(self, subscription_id: str) -> Optional[models.BillingSubscription]:
        """Get subscription by internal ID"""
        return self.db.query(models.BillingSubscription).filter(
            models.BillingSubscription.id == subscription_id
        ).first()
    
    async def get_subscription_by_external_id(self, external_subscription_id: str) -> Optional[models.BillingSubscription]:
        """Get subscription by external provider ID"""
        return self.db.query(models.BillingSubscription).filter(
            models.BillingSubscription.external_subscription_id == external_subscription_id
        ).first()
    
    async def create_or_update_subscription(
        self,
        customer_id: str,
        subscription_data: Dict[str, Any]
    ) -> models.BillingSubscription:
        """
        Create or update subscription record from provider data.
        
        Args:
            customer_id: Internal billing customer ID
            subscription_data: Subscription data from payment provider
            
        Returns:
            Created or updated BillingSubscription
        """
        external_subscription_id = subscription_data.get("id")
        
        # Check if subscription already exists
        existing = await self.get_subscription_by_external_id(external_subscription_id)
        
        if existing:
            # Update existing subscription
            existing.status = subscription_data.get("status", "active")
            existing.current_period_start = self._parse_timestamp(subscription_data.get("current_period_start"))
            existing.current_period_end = self._parse_timestamp(subscription_data.get("current_period_end"))
            existing.metadata = subscription_data.get("metadata", {})
            existing.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Updated subscription {existing.id}")
            return existing
        else:
            # Create new subscription
            subscription = models.BillingSubscription(
                id=str(uuid.uuid4()),
                customer_id=customer_id,
                external_subscription_id=external_subscription_id,
                plan_id=self._extract_plan_id(subscription_data),
                status=subscription_data.get("status", "active"),
                current_period_start=self._parse_timestamp(subscription_data.get("current_period_start")),
                current_period_end=self._parse_timestamp(subscription_data.get("current_period_end")),
                metadata=subscription_data.get("metadata", {})
            )
            
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
            
            logger.info(f"Created subscription {subscription.id}")
            return subscription
    
    async def cancel_subscription_for_org(self, org_id: str) -> bool:
        """
        Cancel subscription for an organization.
        
        Args:
            org_id: Organization ID
            
        Returns:
            True if subscription was canceled, False if no subscription found
        """
        subscription = await self.get_subscription_for_org(org_id)
        if not subscription:
            return False
        
        try:
            # Cancel with payment provider
            await self.payment_provider.cancel_subscription(subscription.external_subscription_id)
            
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
    
    async def cancel_subscription_by_id(self, subscription_id: str) -> bool:
        """
        Cancel subscription by internal ID.
        
        Args:
            subscription_id: Internal subscription ID
            
        Returns:
            True if subscription was canceled, False if not found
        """
        subscription = await self.get_subscription_by_id(subscription_id)
        if not subscription:
            return False
        
        try:
            # Cancel with payment provider
            await self.payment_provider.cancel_subscription(subscription.external_subscription_id)
            
            # Update local record
            subscription.status = "canceled"
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Canceled subscription {subscription_id}")
            return True
            
        except PaymentProviderError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            self.db.rollback()
            raise
    
    async def update_subscription_status(
        self,
        external_subscription_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[models.BillingSubscription]:
        """
        Update subscription status (typically called from webhooks).
        
        Args:
            external_subscription_id: External provider subscription ID
            status: New status
            metadata: Optional metadata to update
            
        Returns:
            Updated subscription or None if not found
        """
        subscription = await self.get_subscription_by_external_id(external_subscription_id)
        if not subscription:
            return None
        
        subscription.status = status
        subscription.updated_at = datetime.utcnow()
        
        if metadata:
            subscription.metadata = {**(subscription.metadata or {}), **metadata}
        
        self.db.commit()
        logger.info(f"Updated subscription {subscription.id} status to {status}")
        return subscription
    
    async def get_subscription_usage_item_id(self, org_id: str) -> Optional[str]:
        """
        Get the metered usage item ID for an organization's subscription.
        
        Args:
            org_id: Organization ID
            
        Returns:
            Usage item ID or None if not found
        """
        subscription = await self.get_subscription_for_org(org_id)
        if not subscription or not subscription.metadata:
            return None
        
        return subscription.metadata.get("metered_item_id")
    
    def _parse_timestamp(self, timestamp: Optional[int]) -> Optional[datetime]:
        """Parse Unix timestamp to datetime"""
        if timestamp is None:
            return None
        return datetime.fromtimestamp(timestamp)
    
    def _extract_plan_id(self, subscription_data: Dict[str, Any]) -> str:
        """Extract plan ID from subscription data"""
        # Handle different provider formats
        items = subscription_data.get("items", {})
        if isinstance(items, dict) and "data" in items:
            items_data = items["data"]
            if items_data and len(items_data) > 0:
                price = items_data[0].get("price", {})
                if isinstance(price, dict):
                    return price.get("id", "")
        
        # Fallback
        return subscription_data.get("plan_id", "")
