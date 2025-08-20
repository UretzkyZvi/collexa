"""
Configuration settings for the Collexa backend application.

This module centralizes all configuration and environment variable handling
to make the application more maintainable and testable.
"""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    
    # Payment Configuration
    PAYMENT_PROVIDER: str = os.getenv("PAYMENT_PROVIDER", "mock")  # default to mock for dev/test
    
    # Stripe Settings
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # PayPal Settings (for future use)
    PAYPAL_CLIENT_ID: Optional[str] = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET: Optional[str] = os.getenv("PAYPAL_CLIENT_SECRET")
    PAYPAL_WEBHOOK_ID: Optional[str] = os.getenv("PAYPAL_WEBHOOK_ID")
    
    # Square Settings (for future use)
    SQUARE_ACCESS_TOKEN: Optional[str] = os.getenv("SQUARE_ACCESS_TOKEN")
    SQUARE_APPLICATION_ID: Optional[str] = os.getenv("SQUARE_APPLICATION_ID")
    SQUARE_WEBHOOK_SIGNATURE_KEY: Optional[str] = os.getenv("SQUARE_WEBHOOK_SIGNATURE_KEY")
    
    # Security & Auth
    MANIFEST_JWKS_JSON: Optional[str] = os.getenv("MANIFEST_JWKS_JSON")
    MANIFEST_PUBLIC_KEY_PEM: Optional[str] = os.getenv("MANIFEST_PUBLIC_KEY_PEM")
    MANIFEST_PRIVATE_KEY_PEM: Optional[str] = os.getenv("MANIFEST_PRIVATE_KEY_PEM")
    MANIFEST_KEY_ID: Optional[str] = os.getenv("MANIFEST_KEY_ID", "dev-key")
    
    # OPA (Open Policy Agent)
    OPA_URL: str = os.getenv("OPA_URL", "http://localhost:8181")
    
    # Application
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Celery Configuration
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Notification Settings (Apprise)
    SMTP_SERVER: Optional[str] = os.getenv("SMTP_SERVER")
    SMTP_PORT: Optional[int] = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASS: Optional[str] = os.getenv("SMTP_PASS")
    SMTP_TO: Optional[str] = os.getenv("SMTP_TO")  # Default recipient

    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")
    TEAMS_WEBHOOK_URL: Optional[str] = os.getenv("TEAMS_WEBHOOK_URL")
    CUSTOM_WEBHOOK_URL: Optional[str] = os.getenv("CUSTOM_WEBHOOK_URL")
    
    @property
    def is_stripe_configured(self) -> bool:
        """Check if Stripe is properly configured"""
        return bool(self.STRIPE_SECRET_KEY)
    
    @property
    def is_paypal_configured(self) -> bool:
        """Check if PayPal is properly configured"""
        return bool(self.PAYPAL_CLIENT_ID and self.PAYPAL_CLIENT_SECRET)
    
    @property
    def is_square_configured(self) -> bool:
        """Check if Square is properly configured"""
        return bool(self.SQUARE_ACCESS_TOKEN and self.SQUARE_APPLICATION_ID)
    
    def validate_payment_provider(self) -> bool:
        """Validate that the selected payment provider is properly configured"""
        if self.PAYMENT_PROVIDER == "stripe":
            return self.is_stripe_configured
        elif self.PAYMENT_PROVIDER == "paypal":
            return self.is_paypal_configured
        elif self.PAYMENT_PROVIDER == "square":
            return self.is_square_configured
        elif self.PAYMENT_PROVIDER == "mock":
            return True  # Mock provider doesn't need configuration
        return False


# Global settings instance
settings = Settings()
