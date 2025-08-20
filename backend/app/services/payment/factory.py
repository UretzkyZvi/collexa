"""
Payment provider factory for creating and managing payment provider instances.

This module provides a factory pattern for creating payment providers,
allowing the application to switch between different payment systems
through configuration.
"""

from typing import Dict, Type, List
from app.services.payment.protocol import PaymentProvider, PaymentProviderConfigError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PaymentProviderFactory:
    """
    Factory for creating payment provider instances.
    
    This factory allows the application to use different payment providers
    without changing business logic. Providers are registered and can be
    created based on configuration.
    """
    
    _providers: Dict[str, Type[PaymentProvider]] = {}
    _instances: Dict[str, PaymentProvider] = {}  # Singleton instances
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[PaymentProvider]):
        """
        Register a payment provider class.
        
        Args:
            name: Provider name (e.g., "stripe", "paypal")
            provider_class: Provider class that implements PaymentProvider
        """
        cls._providers[name] = provider_class
        logger.info(f"Registered payment provider: {name}")
    
    @classmethod
    def create_provider(cls, provider_name: str = None) -> PaymentProvider:
        """
        Create a payment provider instance.
        
        Args:
            provider_name: Name of the provider to create. If None, uses default from settings.
            
        Returns:
            PaymentProvider instance
            
        Raises:
            PaymentProviderConfigError: If provider is not supported or configuration is invalid
        """
        provider_name = provider_name or settings.PAYMENT_PROVIDER
        
        if not provider_name:
            raise PaymentProviderConfigError(
                "No payment provider specified. Set PAYMENT_PROVIDER environment variable.",
                "unknown"
            )
        
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise PaymentProviderConfigError(
                f"Unsupported payment provider: {provider_name}. Available: {available}",
                provider_name
            )
        
        # Return singleton instance if already created
        if provider_name in cls._instances:
            return cls._instances[provider_name]
        
        # Create new instance
        try:
            provider_class = cls._providers[provider_name]
            instance = provider_class()
            cls._instances[provider_name] = instance
            logger.info(f"Created payment provider instance: {provider_name}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create payment provider {provider_name}: {e}")
            raise PaymentProviderConfigError(
                f"Failed to initialize payment provider: {str(e)}",
                provider_name,
                e
            )
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names"""
        return list(cls._providers.keys())
    
    @classmethod
    def is_provider_available(cls, provider_name: str) -> bool:
        """Check if a provider is available"""
        return provider_name in cls._providers
    
    @classmethod
    def clear_instances(cls):
        """Clear all cached provider instances (useful for testing)"""
        cls._instances.clear()
        logger.debug("Cleared all payment provider instances")


# Auto-register available providers
def _register_available_providers():
    """Register all available payment providers"""
    
    # Register Stripe provider
    try:
        from app.services.payment.providers.stripe_provider import StripeProvider
        PaymentProviderFactory.register_provider("stripe", StripeProvider)
    except ImportError as e:
        logger.warning(f"Stripe provider not available: {e}")
    
    # Register PayPal provider (when implemented)
    try:
        from app.services.payment.providers.paypal_provider import PayPalProvider
        PaymentProviderFactory.register_provider("paypal", PayPalProvider)
    except ImportError:
        logger.debug("PayPal provider not available (not implemented)")
    
    # Register Square provider (when implemented)
    try:
        from app.services.payment.providers.square_provider import SquareProvider
        PaymentProviderFactory.register_provider("square", SquareProvider)
    except ImportError:
        logger.debug("Square provider not available (not implemented)")
    
    # Register Mock provider for testing
    try:
        from app.services.payment.providers.mock_provider import MockProvider
        PaymentProviderFactory.register_provider("mock", MockProvider)
    except ImportError:
        logger.debug("Mock provider not available")


# Register providers on module import
_register_available_providers()


# Convenience function for getting the default provider
def get_payment_provider() -> PaymentProvider:
    """
    Get the default payment provider instance.
    
    Returns:
        PaymentProvider instance based on current configuration
    """
    return PaymentProviderFactory.create_provider()


# Convenience function for testing
def get_mock_provider() -> PaymentProvider:
    """
    Get a mock payment provider for testing.
    
    Returns:
        Mock PaymentProvider instance
    """
    return PaymentProviderFactory.create_provider("mock")
