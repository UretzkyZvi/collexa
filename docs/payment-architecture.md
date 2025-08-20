# Payment System Architecture - Provider Agnostic Design

## Overview

This document outlines a payment-agnostic architecture that allows Collexa to support multiple payment providers (Stripe, PayPal, Square, etc.) without tight coupling to any specific vendor.

## Core Principles

1. **Provider Independence**: Business logic should not depend on specific payment provider APIs
2. **Configurable**: Payment provider should be configurable via environment variables
3. **Extensible**: Adding new providers should require minimal changes to existing code
4. **Testable**: Payment logic should be easily mockable for testing
5. **Consistent**: All providers should expose the same interface to the application

## Architecture Components

### 1. Payment Service Protocol (Abstract Interface)

```python
# backend/app/services/payment/protocol.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

class PaymentStatus(Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded" 
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"

class SubscriptionStatus(Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"

@dataclass
class Customer:
    id: str
    email: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class PaymentMethod:
    id: str
    type: str  # "card", "bank_account", etc.
    last4: Optional[str] = None
    brand: Optional[str] = None

@dataclass
class Subscription:
    id: str
    customer_id: str
    status: SubscriptionStatus
    current_period_start: int
    current_period_end: int
    plan_id: str
    metadata: Dict[str, Any] = None

@dataclass
class Invoice:
    id: str
    customer_id: str
    amount_cents: int
    status: PaymentStatus
    due_date: Optional[int] = None
    paid_at: Optional[int] = None

@dataclass
class CheckoutSession:
    id: str
    url: str
    customer_id: Optional[str] = None
    metadata: Dict[str, Any] = None

class PaymentProvider(ABC):
    """Abstract payment provider interface"""
    
    @abstractmethod
    async def create_customer(self, email: str, name: Optional[str] = None, 
                            metadata: Dict[str, Any] = None) -> Customer:
        """Create a new customer"""
        pass
    
    @abstractmethod
    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID"""
        pass
    
    @abstractmethod
    async def create_checkout_session(self, customer_id: str, plan_id: str,
                                    success_url: str, cancel_url: str,
                                    metadata: Dict[str, Any] = None) -> CheckoutSession:
        """Create a checkout session for subscription"""
        pass
    
    @abstractmethod
    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID"""
        pass
    
    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> Subscription:
        """Cancel a subscription"""
        pass
    
    @abstractmethod
    async def create_usage_record(self, subscription_item_id: str, 
                                quantity: int, timestamp: Optional[int] = None) -> bool:
        """Record usage for metered billing"""
        pass
    
    @abstractmethod
    async def get_invoices(self, customer_id: str, limit: int = 10) -> List[Invoice]:
        """Get customer invoices"""
        pass
    
    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str, 
                                secret: str) -> Dict[str, Any]:
        """Verify and parse webhook payload"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name for logging/debugging"""
        pass
```

### 2. Internal Billing Models (Provider-Agnostic)

```python
# backend/app/models/billing.py
from sqlalchemy import Column, String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base

class BillingCustomer(Base):
    """Internal customer representation - maps to external provider"""
    __tablename__ = "billing_customers"
    
    id = Column(String(64), primary_key=True)
    org_id = Column(String(64), ForeignKey("orgs.id"), nullable=False)
    provider = Column(String(32), nullable=False)  # "stripe", "paypal", etc.
    external_customer_id = Column(String(255), nullable=False)  # Provider's customer ID
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BillingSubscription(Base):
    """Internal subscription representation"""
    __tablename__ = "billing_subscriptions"
    
    id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), ForeignKey("billing_customers.id"), nullable=False)
    external_subscription_id = Column(String(255), nullable=False)
    plan_id = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BillingEvent(Base):
    """Provider-agnostic billing events for audit trail"""
    __tablename__ = "billing_events"
    
    id = Column(String(64), primary_key=True)
    org_id = Column(String(64), ForeignKey("orgs.id"), nullable=False)
    customer_id = Column(String(64), ForeignKey("billing_customers.id"))
    event_type = Column(String(64), nullable=False)  # "subscription.created", "payment.succeeded"
    provider = Column(String(32), nullable=False)
    external_event_id = Column(String(255))  # Provider's event ID
    amount_cents = Column(Integer)
    metadata = Column(JSON)
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 3. Provider Factory & Configuration

```python
# backend/app/services/payment/factory.py
from typing import Dict, Type
from app.services.payment.protocol import PaymentProvider
from app.services.payment.providers.stripe_provider import StripeProvider
from app.services.payment.providers.paypal_provider import PayPalProvider
from app.core.config import settings

class PaymentProviderFactory:
    """Factory for creating payment provider instances"""
    
    _providers: Dict[str, Type[PaymentProvider]] = {
        "stripe": StripeProvider,
        "paypal": PayPalProvider,
        # Add more providers here
    }
    
    @classmethod
    def create_provider(cls, provider_name: str = None) -> PaymentProvider:
        """Create a payment provider instance"""
        provider_name = provider_name or settings.PAYMENT_PROVIDER
        
        if provider_name not in cls._providers:
            raise ValueError(f"Unsupported payment provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        return provider_class()
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[PaymentProvider]):
        """Register a new payment provider"""
        cls._providers[name] = provider_class
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available providers"""
        return list(cls._providers.keys())
```

### 4. Configuration

```python
# backend/app/core/config.py (additions)
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Payment Configuration
    PAYMENT_PROVIDER: str = "stripe"  # Default to Stripe
    
    # Stripe Settings (only loaded if provider is stripe)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # PayPal Settings (only loaded if provider is paypal)
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_WEBHOOK_ID: Optional[str] = None
    
    # Square Settings (only loaded if provider is square)
    SQUARE_ACCESS_TOKEN: Optional[str] = None
    SQUARE_APPLICATION_ID: Optional[str] = None
    SQUARE_WEBHOOK_SIGNATURE_KEY: Optional[str] = None
```

## Benefits of This Architecture

1. **Easy Provider Switching**: Change `PAYMENT_PROVIDER=paypal` and restart
2. **Provider-Specific Features**: Each provider can expose unique capabilities while maintaining common interface
3. **Testing**: Mock the `PaymentProvider` interface for unit tests
4. **Gradual Migration**: Can migrate customers from one provider to another
5. **Multi-Provider Support**: Could even support multiple providers simultaneously for different regions/customers

## Implementation Plan

1. **Phase 1**: Implement the abstract interface and Stripe provider
2. **Phase 2**: Refactor existing billing code to use the new architecture
3. **Phase 3**: Add additional providers (PayPal, Square) as needed
4. **Phase 4**: Add multi-provider support if required

## Migration Strategy

For existing Stripe-specific code:
1. Keep current `stripe_customer_id` in orgs table for backward compatibility
2. Populate new `billing_customers` table with existing data
3. Gradually migrate endpoints to use new service layer
4. Remove Stripe-specific fields once migration is complete

This approach allows you to start with Stripe (as planned) while maintaining complete flexibility for the future.
