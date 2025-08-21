"""
Payment provider protocol and data models.

This module defines the abstract interface that all payment providers must implement,
along with common data models used across the payment system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class PaymentStatus(Enum):
    """Standard payment status across all providers"""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class SubscriptionStatus(Enum):
    """Standard subscription status across all providers"""

    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"


@dataclass
class Customer:
    """Provider-agnostic customer representation"""

    id: str
    email: str
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PaymentMethod:
    """Provider-agnostic payment method representation"""

    id: str
    type: str  # "card", "bank_account", etc.
    last4: Optional[str] = None
    brand: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Subscription:
    """Provider-agnostic subscription representation"""

    id: str
    customer_id: str
    status: SubscriptionStatus
    current_period_start: int  # Unix timestamp
    current_period_end: int  # Unix timestamp
    plan_id: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Invoice:
    """Provider-agnostic invoice representation"""

    id: str
    customer_id: str
    amount_cents: int
    status: PaymentStatus
    due_date: Optional[int] = None  # Unix timestamp
    paid_at: Optional[int] = None  # Unix timestamp
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CheckoutSession:
    """Provider-agnostic checkout session representation"""

    id: str
    url: str
    customer_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WebhookEvent:
    """Provider-agnostic webhook event representation"""

    id: str
    type: str
    data: Dict[str, Any]
    created: int  # Unix timestamp
    provider: str


class PaymentProvider(ABC):
    """
    Abstract payment provider interface.

    All payment providers must implement this interface to ensure
    consistent behavior across different payment systems.
    """

    @abstractmethod
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        """Create a new customer in the payment provider"""

    @abstractmethod
    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by provider-specific ID"""

    @abstractmethod
    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Customer:
        """Update customer information"""

    @abstractmethod
    async def create_checkout_session(
        self,
        customer_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CheckoutSession:
        """Create a checkout session for subscription signup"""

    @abstractmethod
    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by provider-specific ID"""

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> Subscription:
        """Cancel a subscription"""

    @abstractmethod
    async def create_usage_record(
        self, subscription_item_id: str, quantity: int, timestamp: Optional[int] = None
    ) -> bool:
        """Record usage for metered billing"""

    @abstractmethod
    async def get_invoices(self, customer_id: str, limit: int = 10) -> List[Invoice]:
        """Get customer invoices"""

    @abstractmethod
    def verify_webhook_signature(
        self, payload: bytes, signature: str, secret: str
    ) -> WebhookEvent:
        """Verify webhook signature and parse event"""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name for logging/debugging"""

    @abstractmethod
    def get_dashboard_url(self, customer_id: str) -> Optional[str]:
        """Get URL to customer dashboard (if supported)"""


class PaymentProviderError(Exception):
    """Base exception for payment provider errors"""

    def __init__(
        self, message: str, provider: str, original_error: Optional[Exception] = None
    ):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")


class CustomerNotFoundError(PaymentProviderError):
    """Raised when customer is not found"""


class SubscriptionNotFoundError(PaymentProviderError):
    """Raised when subscription is not found"""


class WebhookVerificationError(PaymentProviderError):
    """Raised when webhook signature verification fails"""


class PaymentProviderConfigError(PaymentProviderError):
    """Raised when provider configuration is invalid"""
