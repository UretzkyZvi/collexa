from fastapi import APIRouter

router = APIRouter()

@router.post("/billing/checkout")
async def billing_checkout():
    # TODO: integrate Stripe Checkout
    return {"url": "https://billing.example.com/checkout-session"}

