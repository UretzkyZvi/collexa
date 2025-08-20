# Payment Provider Examples

This document shows how to use the payment-agnostic billing system with different providers.

## Configuration

Set the payment provider via environment variable:

```bash
# Use Stripe (default)
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Use Mock provider for testing
PAYMENT_PROVIDER=mock

# Use PayPal (when implemented)
PAYMENT_PROVIDER=paypal
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_CLIENT_SECRET=your_client_secret
```

## Using the Billing Service

The billing service works the same way regardless of the payment provider:

```python
from app.services.billing_service import BillingService
from app.db.session import get_db

# Create billing service (automatically uses configured provider)
db = next(get_db())
billing_service = BillingService(db)

# Create customer for organization
billing_customer = await billing_service.create_customer_for_org(
    org_id="org_123",
    email="billing@company.com",
    name="Company Name"
)

# Create checkout session
checkout_session = await billing_service.create_checkout_session(
    org_id="org_123",
    plan_id="price_monthly_pro",
    success_url="https://yourapp.com/billing/success",
    cancel_url="https://yourapp.com/billing/cancel"
)

# Redirect user to checkout_session.url
print(f"Redirect to: {checkout_session.url}")
```

## API Usage

The REST API is also provider-agnostic:

```bash
# Create checkout session
curl -X POST http://localhost:8000/v1/billing/checkout \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "price_monthly_pro",
    "success_url": "https://yourapp.com/success",
    "cancel_url": "https://yourapp.com/cancel"
  }'

# Get subscription status
curl -X GET http://localhost:8000/v1/billing/subscription \
  -H "Authorization: Bearer your_jwt_token"

# Cancel subscription
curl -X DELETE http://localhost:8000/v1/billing/subscription \
  -H "Authorization: Bearer your_jwt_token"
```

## Provider-Specific Features

While the core interface is the same, providers may have unique features:

### Stripe-Specific Features

```python
from app.services.payment.factory import get_payment_provider

provider = get_payment_provider()
if provider.get_provider_name() == "stripe":
    # Access Stripe-specific features
    dashboard_url = provider.get_dashboard_url(customer_id)
    print(f"View customer in Stripe: {dashboard_url}")
```

### Mock Provider for Testing

```python
from app.services.payment.providers.mock_provider import MockProvider

# Create mock provider for testing
mock_provider = MockProvider()

# Simulate webhook events
webhook_event = mock_provider.simulate_webhook_event(
    event_type="customer.subscription.created",
    data={
        "object": {
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active"
        }
    }
)

# Clear test data
mock_provider.clear_all_data()
```

## Switching Providers

To switch from one provider to another:

1. **Update environment variables:**
   ```bash
   # Change from Stripe to PayPal
   PAYMENT_PROVIDER=paypal
   PAYPAL_CLIENT_ID=your_paypal_client_id
   PAYPAL_CLIENT_SECRET=your_paypal_secret
   ```

2. **Restart the application** - the new provider will be loaded automatically

3. **Migrate existing customers** (if needed):
   ```python
   # Example migration script
   from app.services.billing_service import BillingService
   from app.services.payment.factory import PaymentProviderFactory
   
   # Get old and new providers
   old_provider = PaymentProviderFactory.create_provider("stripe")
   new_provider = PaymentProviderFactory.create_provider("paypal")
   
   # Migrate customers (implementation depends on providers)
   # This would be a custom migration script
   ```

## Adding New Providers

To add a new payment provider:

1. **Create provider implementation:**
   ```python
   # backend/app/services/payment/providers/square_provider.py
   from app.services.payment.protocol import PaymentProvider
   
   class SquareProvider(PaymentProvider):
       def get_provider_name(self) -> str:
           return "square"
       
       async def create_customer(self, email, name=None, metadata=None):
           # Implement Square API calls
           pass
       
       # Implement other required methods...
   ```

2. **Register the provider:**
   ```python
   # In backend/app/services/payment/factory.py
   from app.services.payment.providers.square_provider import SquareProvider
   PaymentProviderFactory.register_provider("square", SquareProvider)
   ```

3. **Add configuration:**
   ```python
   # In backend/app/core/config.py
   SQUARE_ACCESS_TOKEN: Optional[str] = os.getenv("SQUARE_ACCESS_TOKEN")
   SQUARE_APPLICATION_ID: Optional[str] = os.getenv("SQUARE_APPLICATION_ID")
   ```

4. **Test the new provider:**
   ```python
   # Set environment variable
   PAYMENT_PROVIDER=square
   
   # Use normally - no code changes needed!
   billing_service = BillingService(db)
   customer = await billing_service.create_customer_for_org(...)
   ```

## Benefits

This architecture provides:

- **Vendor Independence**: Switch providers without code changes
- **Testing**: Use mock provider for development and testing
- **Flexibility**: Support multiple providers simultaneously (future)
- **Consistency**: Same API regardless of underlying provider
- **Extensibility**: Easy to add new providers

## Migration Strategy

For existing Stripe-only deployments:

1. **Phase 1**: Deploy the new architecture with `PAYMENT_PROVIDER=stripe`
2. **Phase 2**: Run migration to populate new billing tables
3. **Phase 3**: Switch to new API endpoints
4. **Phase 4**: Remove old Stripe-specific code
5. **Phase 5**: Add additional providers as needed

This ensures zero downtime and backward compatibility during the transition.
