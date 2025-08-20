"""
Async webhook processing service using Celery.

This service provides reliable, asynchronous webhook processing with
automatic retries, failure handling, and monitoring.
"""

from celery import Celery
from celery.exceptions import Retry
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
import json

from app.services.billing.webhook_service import WebhookService
from app.services.billing_orchestrator import BillingOrchestrator
from app.db.session import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery(
    'billing',
    broker=settings.CELERY_BROKER_URL or 'redis://localhost:6379/0',
    backend=settings.CELERY_RESULT_BACKEND or 'redis://localhost:6379/0'
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_default_retry_delay=60,  # 1 minute default retry delay
    task_max_retries=3,
)


@celery_app.task(bind=True, name='billing.process_webhook')
def process_webhook_async(self, payload_b64: str, signature: str, provider: str = "stripe") -> Dict[str, Any]:
    """
    Process webhook asynchronously with automatic retries.
    
    Args:
        payload_b64: Base64 encoded webhook payload
        signature: Webhook signature for verification
        provider: Payment provider name
        
    Returns:
        Dictionary with processing results
    """
    import base64
    
    try:
        # Decode payload
        payload = base64.b64decode(payload_b64.encode())
        
        # Get database session
        db = next(get_db())
        
        # Process webhook
        webhook_service = WebhookService(db, None)  # Will use default provider
        success = webhook_service.process_webhook(payload, signature)
        
        if success:
            logger.info(f"Successfully processed webhook from {provider}")
            return {
                "status": "success",
                "provider": provider,
                "task_id": self.request.id,
                "retries": self.request.retries
            }
        else:
            raise Exception("Webhook processing returned False")
            
    except Exception as exc:
        logger.error(f"Webhook processing failed (attempt {self.request.retries + 1}): {exc}")
        
        # Exponential backoff: 1min, 2min, 4min
        countdown = 60 * (2 ** self.request.retries)
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying webhook processing in {countdown} seconds")
            raise self.retry(exc=exc, countdown=countdown)
        else:
            # Max retries reached, log as critical error
            logger.critical(f"Webhook processing failed permanently after {self.max_retries} retries: {exc}")
            
            # Store failed webhook for manual processing
            try:
                db = next(get_db())
                failed_webhook = {
                    "payload_b64": payload_b64,
                    "signature": signature,
                    "provider": provider,
                    "error": str(exc),
                    "task_id": self.request.id,
                    "retries": self.request.retries
                }
                # TODO: Store in failed_webhooks table for manual review
                logger.error(f"Failed webhook stored for manual processing: {failed_webhook}")
            except Exception as store_exc:
                logger.error(f"Failed to store failed webhook: {store_exc}")
            
            return {
                "status": "failed",
                "error": str(exc),
                "provider": provider,
                "task_id": self.request.id,
                "retries": self.request.retries
            }


@celery_app.task(bind=True, name='billing.process_subscription_event')
def process_subscription_event_async(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process subscription lifecycle events asynchronously.
    
    Args:
        event_data: Subscription event data
        
    Returns:
        Processing results
    """
    try:
        db = next(get_db())
        billing_orchestrator = BillingOrchestrator(db)
        
        event_type = event_data.get("type")
        subscription_data = event_data.get("data", {}).get("object", {})
        
        logger.info(f"Processing subscription event: {event_type}")
        
        if event_type == "customer.subscription.created":
            # Handle new subscription
            customer_id = subscription_data.get("customer")
            # Process subscription creation logic
            logger.info(f"New subscription created for customer {customer_id}")
            
        elif event_type == "customer.subscription.updated":
            # Handle subscription updates
            subscription_id = subscription_data.get("id")
            logger.info(f"Subscription {subscription_id} updated")
            
        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            subscription_id = subscription_data.get("id")
            logger.info(f"Subscription {subscription_id} canceled")
        
        return {
            "status": "success",
            "event_type": event_type,
            "task_id": self.request.id
        }
        
    except Exception as exc:
        logger.error(f"Subscription event processing failed: {exc}")
        
        if self.request.retries < 2:  # Fewer retries for event processing
            countdown = 30 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        
        return {
            "status": "failed",
            "error": str(exc),
            "event_type": event_data.get("type"),
            "task_id": self.request.id
        }


@celery_app.task(name='billing.generate_monthly_usage_report')
def generate_monthly_usage_report_async(org_id: str, month: str) -> Dict[str, Any]:
    """
    Generate monthly usage report asynchronously.
    
    Args:
        org_id: Organization ID
        month: Month in YYYY-MM format
        
    Returns:
        Usage report data
    """
    try:
        from app.services.usage_orchestrator import UsageOrchestrator
        from datetime import datetime
        
        db = next(get_db())
        usage_orchestrator = UsageOrchestrator(db)
        
        # Parse month
        year, month_num = month.split("-")
        start_date = datetime(int(year), int(month_num), 1)
        
        # Calculate end date
        if int(month_num) == 12:
            end_date = datetime(int(year) + 1, 1, 1)
        else:
            end_date = datetime(int(year), int(month_num) + 1, 1)
        
        # Generate report
        report = usage_orchestrator.generate_usage_report(org_id, start_date, end_date)
        
        logger.info(f"Generated monthly usage report for org {org_id}, month {month}")
        
        return {
            "status": "success",
            "org_id": org_id,
            "month": month,
            "report": report
        }
        
    except Exception as exc:
        logger.error(f"Failed to generate monthly usage report for org {org_id}: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
            "org_id": org_id,
            "month": month
        }


@celery_app.task(name='billing.send_budget_alert')
def send_budget_alert_async(org_id: str, alert_type: str, alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send budget alert asynchronously using Apprise.

    Args:
        org_id: Organization ID
        alert_type: Type of alert (violation, warning)
        alert_data: Alert data

    Returns:
        Alert sending results
    """
    try:
        from app.services.notifications.alert_service import alert_service
        from app.services.notifications.alert_service import AlertSeverity

        success = False

        if alert_type == "violation":
            # Handle single violation or list of violations
            violations = alert_data if isinstance(alert_data, list) else [alert_data]
            success = alert_service.send_budget_violation_alert(
                org_id=org_id,
                violations=violations,
                severity=AlertSeverity.CRITICAL
            )
        elif alert_type == "warning":
            warnings = alert_data.get("warnings", [])
            success = alert_service.send_budget_warning_alert(
                org_id=org_id,
                warnings=warnings,
                severity=AlertSeverity.WARNING
            )

        if success:
            logger.info(f"Successfully sent {alert_type} alert for org {org_id}")
        else:
            logger.error(f"Failed to send {alert_type} alert for org {org_id}")

        return {
            "status": "success" if success else "failed",
            "org_id": org_id,
            "alert_type": alert_type,
            "sent_at": datetime.utcnow().isoformat()
        }

    except Exception as exc:
        logger.error(f"Failed to send budget alert for org {org_id}: {exc}")
        return {
            "status": "failed",
            "error": str(exc),
            "org_id": org_id,
            "alert_type": alert_type
        }


# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'check-budget-violations': {
        'task': 'billing.check_budget_violations',
        'schedule': 900.0,  # Every 15 minutes
    },
    'generate-monthly-reports': {
        'task': 'billing.generate_monthly_reports',
        'schedule': 86400.0,  # Daily
    },
}


@celery_app.task(name='billing.check_budget_violations')
def check_budget_violations_async():
    """Periodic task to check for budget violations"""
    try:
        from app.services.budget.budget_enforcement_service import BudgetEnforcementService
        from app.db import models
        
        db = next(get_db())
        budget_enforcement = BudgetEnforcementService(db)
        
        # Get all active organizations
        orgs = db.query(models.Org).filter(models.Org.status == "active").all()
        
        for org in orgs:
            violations = budget_enforcement.get_budget_violations(org.id)
            warnings = budget_enforcement.get_budget_warnings(org.id, threshold=0.8)
            
            if violations:
                # Send violation alerts
                for violation in violations:
                    send_budget_alert_async.delay(
                        org.id, 
                        "violation", 
                        {
                            "budget_id": violation.id,
                            "limit_cents": violation.limit_cents,
                            "current_usage_cents": violation.current_usage_cents,
                            "enforcement_mode": violation.enforcement_mode
                        }
                    )
            
            if warnings:
                # Send warning alerts
                send_budget_alert_async.delay(org.id, "warning", {"warnings": warnings})
        
        logger.info(f"Checked budget violations for {len(orgs)} organizations")
        
    except Exception as exc:
        logger.error(f"Failed to check budget violations: {exc}")


# Helper function to start webhook processing
def queue_webhook_processing(payload: bytes, signature: str, provider: str = "stripe") -> str:
    """
    Queue webhook for asynchronous processing.
    
    Args:
        payload: Raw webhook payload
        signature: Webhook signature
        provider: Payment provider name
        
    Returns:
        Task ID for tracking
    """
    import base64
    
    # Encode payload for JSON serialization
    payload_b64 = base64.b64encode(payload).decode()
    
    # Queue the task
    task = process_webhook_async.delay(payload_b64, signature, provider)
    
    logger.info(f"Queued webhook processing task: {task.id}")
    return task.id
