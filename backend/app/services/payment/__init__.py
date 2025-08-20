"""
Payment service package for Collexa.

This package provides a payment-agnostic interface for handling billing
operations across different payment providers.
"""

from .factory import PaymentProviderFactory, get_payment_provider, get_mock_provider
from .protocol import (
    PaymentProvider, Customer, Subscription, Invoice, CheckoutSession,
    PaymentStatus, SubscriptionStatus, PaymentProviderError
)

__all__ = [
    "PaymentProviderFactory",
    "get_payment_provider", 
    "get_mock_provider",
    "PaymentProvider",
    "Customer",
    "Subscription", 
    "Invoice",
    "CheckoutSession",
    "PaymentStatus",
    "SubscriptionStatus",
    "PaymentProviderError"
]
