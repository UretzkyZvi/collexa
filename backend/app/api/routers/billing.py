from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.services.billing_orchestrator import BillingOrchestrator
from app.services.payment.protocol import PaymentProviderError
from app.api.deps import get_current_org_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class CheckoutRequest(BaseModel):
    plan_id: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class WebhookRequest(BaseModel):
    # This will be populated from the raw request body
    pass


@router.post("/billing/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """
    Create a checkout session for subscription signup.

    This endpoint is payment provider agnostic - it will work with
    Stripe, PayPal, Square, or any other configured provider.
    """
    try:
        billing_orchestrator = BillingOrchestrator(db)

        # Use default URLs if not provided
        success_url = request.success_url or "http://localhost:3000/billing/success"
        cancel_url = request.cancel_url or "http://localhost:3000/billing/cancel"

        checkout_session = await billing_orchestrator.create_subscription_checkout(
            org_id=org_id,
            plan_id=request.plan_id,
            success_url=success_url,
            cancel_url=cancel_url
        )

        return {
            "checkout_session_id": checkout_session.id,
            "url": checkout_session.url
        }

    except PaymentProviderError as e:
        logger.error(f"Payment provider error creating checkout session: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/billing/webhooks")
async def handle_billing_webhook(
    request: Request,
    use_async: bool = True
):
    """
    Handle billing webhooks from payment providers.

    This endpoint supports both synchronous and asynchronous processing.
    Async processing (default) provides better reliability and retry handling.
    """
    try:
        # Get raw body and signature header
        body = await request.body()
        signature = request.headers.get("stripe-signature") or request.headers.get("paypal-signature") or ""

        if use_async:
            # Queue for asynchronous processing with Celery
            from app.services.billing.async_webhook_service import queue_webhook_processing

            task_id = queue_webhook_processing(body, signature, "stripe")

            return {
                "status": "queued",
                "task_id": task_id,
                "message": "Webhook queued for processing"
            }
        else:
            # Synchronous processing (fallback)
            db = next(get_db())
            billing_orchestrator = BillingOrchestrator(db)
            success = await billing_orchestrator.process_webhook_event(body, signature)

            if success:
                return {"status": "success"}
            else:
                raise HTTPException(status_code=400, detail="Failed to process webhook")

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


@router.get("/billing/webhooks/{task_id}/status")
async def get_webhook_task_status(task_id: str):
    """
    Get the status of an asynchronous webhook processing task.

    Args:
        task_id: Task ID returned from webhook endpoint

    Returns:
        Task status and results
    """
    try:
        from app.services.billing.async_webhook_service import celery_app

        task = celery_app.AsyncResult(task_id)

        if task.state == 'PENDING':
            response = {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is waiting to be processed"
            }
        elif task.state == 'PROGRESS':
            response = {
                "task_id": task_id,
                "status": "processing",
                "message": "Task is being processed"
            }
        elif task.state == 'SUCCESS':
            response = {
                "task_id": task_id,
                "status": "success",
                "result": task.result
            }
        elif task.state == 'FAILURE':
            response = {
                "task_id": task_id,
                "status": "failed",
                "error": str(task.info)
            }
        else:
            response = {
                "task_id": task_id,
                "status": task.state,
                "message": f"Task state: {task.state}"
            }

        return response

    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")


@router.get("/billing/subscription")
async def get_subscription_status(
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """Get current subscription status for the organization"""
    try:
        billing_orchestrator = BillingOrchestrator(db)
        billing_status = await billing_orchestrator.get_organization_billing_status(org_id)

        if not billing_status["has_billing"] or not billing_status["subscription"]:
            return {"status": "no_subscription"}

        subscription = billing_status["subscription"]
        return {
            "subscription_id": subscription["id"],
            "status": subscription["status"],
            "plan_id": subscription["plan_id"],
            "current_period_start": subscription["current_period_start"],
            "current_period_end": subscription["current_period_end"],
            "provider": billing_status["provider"]
        }

    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription status")


@router.delete("/billing/subscription")
async def cancel_subscription(
    org_id: str = Depends(get_current_org_id),
    db: Session = Depends(get_db)
):
    """Cancel the organization's subscription"""
    try:
        billing_orchestrator = BillingOrchestrator(db)
        success = await billing_orchestrator.cancel_organization_subscription(org_id)

        if success:
            return {"status": "canceled"}
        else:
            return {"status": "no_subscription"}

    except PaymentProviderError as e:
        logger.error(f"Payment provider error canceling subscription: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")
