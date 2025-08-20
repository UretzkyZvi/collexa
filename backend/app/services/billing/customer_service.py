"""
Customer management service.

This service handles all customer-related operations including creation,
retrieval, and updates across different payment providers.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.services.payment.factory import get_payment_provider
from app.services.payment.protocol import PaymentProvider, PaymentProviderError
from app.db import models
import logging
import uuid

logger = logging.getLogger(__name__)


class CustomerService:
    """Service for managing billing customers"""
    
    def __init__(self, db: Session, payment_provider: Optional[PaymentProvider] = None):
        self.db = db
        self.payment_provider = payment_provider or get_payment_provider()
    
    async def create_customer_for_org(
        self, 
        org_id: str, 
        email: str, 
        name: Optional[str] = None
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
                email=email,
                name=name,
                metadata={"org_id": org_id}
            )
            
            # Create internal billing customer record
            billing_customer = models.BillingCustomer(
                id=str(uuid.uuid4()),
                org_id=org_id,
                provider=self.payment_provider.get_provider_name(),
                external_customer_id=provider_customer.id,
                email=email,
                name=name,
                metadata_json=provider_customer.metadata
            )
            
            self.db.add(billing_customer)
            self.db.commit()
            self.db.refresh(billing_customer)
            
            # Update org with customer reference (for backward compatibility)
            org = self.db.query(models.Org).filter(models.Org.id == org_id).first()
            if org and self.payment_provider.get_provider_name() == "stripe":
                try:
                    org.stripe_customer_id = provider_customer.id
                    self.db.commit()
                except Exception:
                    pass
            
            logger.info(f"Created billing customer for org {org_id} with provider {self.payment_provider.get_provider_name()}")
            return billing_customer
            
        except PaymentProviderError as e:
            logger.error(f"Failed to create customer for org {org_id}: {e}")
            self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating customer for org {org_id}: {e}")
            self.db.rollback()
            raise
    
    async def get_customer_by_org(self, org_id: str) -> Optional[models.BillingCustomer]:
        """Get billing customer for an organization"""
        return self.db.query(models.BillingCustomer).filter(
            models.BillingCustomer.org_id == org_id
        ).first()
    
    async def get_customer_by_id(self, customer_id: str) -> Optional[models.BillingCustomer]:
        """Get billing customer by ID"""
        return self.db.query(models.BillingCustomer).filter(
            models.BillingCustomer.id == customer_id
        ).first()
    
    async def get_customer_by_external_id(self, external_customer_id: str) -> Optional[models.BillingCustomer]:
        """Get billing customer by external provider ID"""
        return self.db.query(models.BillingCustomer).filter(
            models.BillingCustomer.external_customer_id == external_customer_id
        ).first()
    
    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Optional[models.BillingCustomer]:
        """
        Update customer information both locally and with payment provider.
        
        Args:
            customer_id: Internal customer ID
            email: New email (optional)
            name: New name (optional)
            metadata: New metadata (optional)
            
        Returns:
            Updated BillingCustomer or None if not found
        """
        try:
            # Get local customer record
            billing_customer = await self.get_customer_by_id(customer_id)
            if not billing_customer:
                return None
            
            # Update with payment provider
            provider_customer = await self.payment_provider.update_customer(
                customer_id=billing_customer.external_customer_id,
                email=email,
                name=name,
                metadata=metadata
            )
            
            # Update local record
            if email is not None:
                billing_customer.email = email
            if name is not None:
                billing_customer.name = name
            if metadata is not None:
                billing_customer.metadata = metadata
            
            billing_customer.metadata = provider_customer.metadata
            self.db.commit()
            
            logger.info(f"Updated customer {customer_id}")
            return billing_customer
            
        except PaymentProviderError as e:
            logger.error(f"Failed to update customer {customer_id}: {e}")
            self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating customer {customer_id}: {e}")
            self.db.rollback()
            raise
    
    async def get_or_create_customer_for_org(
        self,
        org_id: str,
        default_email: Optional[str] = None,
        default_name: Optional[str] = None
    ) -> models.BillingCustomer:
        """
        Get existing customer for org or create a new one.
        
        Args:
            org_id: Organization ID
            default_email: Email to use if creating new customer
            default_name: Name to use if creating new customer
            
        Returns:
            BillingCustomer (existing or newly created)
        """
        # Try to get existing customer
        existing_customer = await self.get_customer_by_org(org_id)
        if existing_customer:
            return existing_customer
        
        # Create new customer
        if not default_email:
            # Get org details to generate email
            org = self.db.query(models.Org).filter(models.Org.id == org_id).first()
            if not org:
                raise ValueError(f"Organization {org_id} not found")
            
            default_email = f"billing@{org.name.lower().replace(' ', '')}.com"
            default_name = default_name or org.name
        
        return await self.create_customer_for_org(
            org_id=org_id,
            email=default_email,
            name=default_name
        )
    
    def get_provider_dashboard_url(self, customer_id: str) -> Optional[str]:
        """Get URL to customer dashboard in payment provider"""
        billing_customer = self.db.query(models.BillingCustomer).filter(
            models.BillingCustomer.id == customer_id
        ).first()
        
        if not billing_customer:
            return None
        
        return self.payment_provider.get_dashboard_url(billing_customer.external_customer_id)
