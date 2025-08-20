"""
Payment provider implementations.

This package contains concrete implementations of the PaymentProvider
interface for different payment systems.
"""

# Import providers to make them available for registration
try:
    from .stripe_provider import StripeProvider
except ImportError:
    StripeProvider = None

try:
    from .mock_provider import MockProvider
except ImportError:
    MockProvider = None

# Future providers can be imported here
# from .paypal_provider import PayPalProvider
# from .square_provider import SquareProvider

__all__ = [
    "StripeProvider",
    "MockProvider"
]
