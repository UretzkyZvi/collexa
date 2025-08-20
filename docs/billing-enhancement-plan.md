# Billing System Enhancement Plan with Phase 2 Libraries

## Overview

This document outlines how to enhance our current billing system using recommended Phase 2 libraries to improve reliability, scalability, and developer experience.

## Current State vs Enhanced State

| Feature | Current Implementation | Enhanced with Libraries |
|---------|----------------------|------------------------|
| Webhook Processing | Synchronous, no retries | Celery + Temporal: Async, guaranteed processing |
| Budget Monitoring | Manual checks | APScheduler: Automated monitoring & alerts |
| Budget Enforcement | Pre-request validation | fastapi-limiter: Real-time rate limiting |
| Alerts | Basic logging | Apprise: Multi-channel notifications |
| Usage Aggregation | On-demand queries | Temporal: Scheduled workflows |
| Billing Cycles | Manual processes | Temporal: Automated billing workflows |

## Phase 1: Quick Wins (Week 1-2)

### 1. Add Celery for Webhook Processing

**Benefits**: Reliable webhook processing, automatic retries, failure handling

```python
# backend/app/services/billing/async_webhook_service.py
from celery import Celery
from app.services.billing.webhook_service import WebhookService

celery_app = Celery('billing', broker='redis://localhost:6379')

@celery_app.task(bind=True, max_retries=3)
def process_webhook_async(self, payload: bytes, signature: str, provider: str):
    try:
        webhook_service = WebhookService(get_db())
        return webhook_service.process_webhook(payload, signature)
    except Exception as exc:
        # Exponential backoff: 1min, 2min, 4min
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)

# Updated webhook endpoint
@router.post("/billing/webhooks")
async def handle_billing_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("stripe-signature", "")
    
    # Queue for async processing
    task = process_webhook_async.delay(body, signature, "stripe")
    
    return {"status": "queued", "task_id": task.id}
```

### 2. Add APScheduler for Budget Monitoring

**Benefits**: Automated budget checks, proactive alerts, scheduled maintenance

```python
# backend/app/services/budget/scheduler_service.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.budget.budget_enforcement_service import BudgetEnforcementService

class BudgetSchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.setup_jobs()
    
    def setup_jobs(self):
        # Check budgets every 15 minutes
        self.scheduler.add_job(
            self.check_budget_violations,
            'interval',
            minutes=15,
            id='budget_check'
        )
        
        # Reset daily budgets at midnight
        self.scheduler.add_job(
            self.reset_daily_budgets,
            'cron',
            hour=0,
            minute=0,
            id='daily_budget_reset'
        )
        
        # Generate monthly usage reports
        self.scheduler.add_job(
            self.generate_monthly_reports,
            'cron',
            day=1,
            hour=2,
            id='monthly_reports'
        )
    
    async def check_budget_violations(self):
        db = get_db()
        budget_enforcement = BudgetEnforcementService(db)
        
        # Get all active organizations
        orgs = db.query(models.Org).filter(models.Org.status == "active").all()
        
        for org in orgs:
            violations = budget_enforcement.get_budget_violations(org.id)
            warnings = budget_enforcement.get_budget_warnings(org.id, threshold=0.8)
            
            if violations:
                await self.send_violation_alerts(org, violations)
            if warnings:
                await self.send_warning_alerts(org, warnings)
```

### 3. Add Apprise for Multi-Channel Alerts

**Benefits**: Email, Slack, Discord, webhook notifications

```python
# backend/app/services/notifications/alert_service.py
import apprise
from typing import List, Dict, Any

class AlertService:
    def __init__(self):
        self.apobj = apprise.Apprise()
        self.setup_channels()
    
    def setup_channels(self):
        # Configure from environment variables
        if settings.SMTP_SERVER:
            self.apobj.add(f'mailto://{settings.SMTP_USER}:{settings.SMTP_PASS}@{settings.SMTP_SERVER}')
        
        if settings.SLACK_WEBHOOK:
            self.apobj.add(settings.SLACK_WEBHOOK)
        
        if settings.DISCORD_WEBHOOK:
            self.apobj.add(settings.DISCORD_WEBHOOK)
    
    async def send_budget_violation_alert(self, org_id: str, violations: List[Dict]):
        title = f"🚨 Budget Violation Alert - Organization {org_id}"
        
        body = "The following budgets have been exceeded:\n\n"
        for violation in violations:
            body += f"• {violation['budget_name']}: "
            body += f"${violation['current_usage_cents']/100:.2f} / ${violation['limit_cents']/100:.2f} "
            body += f"({violation['utilization_percent']:.1f}%)\n"
        
        body += f"\nImmediate action required for hard budget violations."
        
        self.apobj.notify(title=title, body=body)
    
    async def send_budget_warning_alert(self, org_id: str, warnings: List[Dict]):
        title = f"⚠️ Budget Warning - Organization {org_id}"
        
        body = "The following budgets are approaching their limits:\n\n"
        for warning in warnings:
            body += f"• {warning['budget_name']}: "
            body += f"${warning['current_usage_cents']/100:.2f} / ${warning['limit_cents']/100:.2f} "
            body += f"({warning['utilization_percent']:.1f}%)\n"
        
        self.apobj.notify(title=title, body=body)
```

## Phase 2: Advanced Workflows (Week 3-4)

### 4. Add Temporal for Complex Billing Workflows

**Benefits**: Guaranteed execution, workflow visibility, complex orchestration

```python
# backend/app/workflows/billing_workflows.py
from temporalio import workflow, activity
from datetime import timedelta

@workflow.defn
class MonthlyBillingWorkflow:
    @workflow.run
    async def run(self, org_id: str, billing_month: str) -> Dict[str, Any]:
        # Step 1: Aggregate usage with retry
        usage_data = await workflow.execute_activity(
            aggregate_monthly_usage,
            args=[org_id, billing_month],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3)
        )
        
        # Step 2: Calculate billing amount
        billing_amount = await workflow.execute_activity(
            calculate_billing_amount,
            args=[usage_data],
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # Step 3: Report to payment provider
        if billing_amount > 0:
            await workflow.execute_activity(
                report_usage_to_provider,
                args=[org_id, billing_amount],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=5,
                    backoff_coefficient=2.0
                )
            )
        
        # Step 4: Generate invoice
        invoice = await workflow.execute_activity(
            generate_invoice,
            args=[org_id, billing_month, usage_data, billing_amount],
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # Step 5: Send notifications
        await workflow.execute_activity(
            send_billing_notifications,
            args=[org_id, invoice],
            start_to_close_timeout=timedelta(minutes=2)
        )
        
        return {
            "org_id": org_id,
            "billing_month": billing_month,
            "total_usage": usage_data,
            "amount_cents": billing_amount,
            "invoice_id": invoice["id"]
        }

@activity.defn
async def aggregate_monthly_usage(org_id: str, billing_month: str) -> Dict[str, Any]:
    usage_orchestrator = UsageOrchestrator(get_db())
    # Implementation details...
    return usage_summary

@activity.defn
async def report_usage_to_provider(org_id: str, amount_cents: int) -> bool:
    billing_orchestrator = BillingOrchestrator(get_db())
    # Implementation details...
    return success
```

### 5. Add fastapi-limiter for Real-time Budget Enforcement

**Benefits**: Distributed rate limiting, Redis-backed quotas, per-org/agent limits

```python
# backend/app/middleware/budget_limiter.py
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis

# Initialize limiter
async def init_limiter():
    redis_client = redis.from_url("redis://localhost:6379")
    await FastAPILimiter.init(redis_client)

# Custom budget-based limiter
class BudgetLimiter:
    def __init__(self, cost_cents: int):
        self.cost_cents = cost_cents
    
    async def __call__(self, org_id: str = Depends(get_current_org_id)):
        budget_enforcement = BudgetEnforcementService(get_db())
        
        # Check if this request would exceed budget
        try:
            budget_enforcement.check_budget_before_usage(
                org_id=org_id,
                estimated_cost_cents=self.cost_cents
            )
        except BudgetExceededException as e:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "budget_exceeded",
                    "budget_id": e.budget_id,
                    "limit_cents": e.limit_cents,
                    "current_usage_cents": e.current_usage_cents
                }
            )
        
        return True

# Apply to endpoints
@router.post("/agents/{agent_id}/invoke")
async def invoke_agent(
    agent_id: str,
    payload: dict,
    _: bool = Depends(BudgetLimiter(cost_cents=10))  # Estimated invocation cost
):
    # ... existing logic
```

## Phase 3: Advanced Features (Week 5-6)

### 6. Add OpenMeter for Advanced Usage Tracking

**Benefits**: High-performance metering, real-time aggregation, billing integration

```python
# backend/app/services/usage/openmeter_service.py
import httpx
from typing import Dict, Any

class OpenMeterService:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=settings.OPENMETER_URL)
        self.api_key = settings.OPENMETER_API_KEY
    
    async def record_usage_event(self, org_id: str, agent_id: str, event_data: Dict[str, Any]):
        """Record usage event to OpenMeter"""
        event = {
            "subject": org_id,
            "type": "agent_invocation",
            "data": {
                "agent_id": agent_id,
                "tokens_input": event_data.get("input_tokens", 0),
                "tokens_output": event_data.get("output_tokens", 0),
                "duration_ms": event_data.get("duration_ms", 0)
            },
            "time": event_data.get("timestamp")
        }
        
        response = await self.client.post(
            "/api/v1/events",
            json=event,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        return response.status_code == 201
    
    async def get_usage_summary(self, org_id: str, start_time: str, end_time: str):
        """Get aggregated usage from OpenMeter"""
        response = await self.client.get(
            f"/api/v1/meters/agent_invocation/query",
            params={
                "subject": org_id,
                "from": start_time,
                "to": end_time,
                "groupBy": ["agent_id"]
            },
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        return response.json()
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Add Celery for webhook processing
- [ ] Add APScheduler for budget monitoring
- [ ] Add Apprise for notifications
- [ ] Update webhook endpoints to use async processing

### Week 2: Integration
- [ ] Implement budget violation monitoring
- [ ] Set up automated budget resets
- [ ] Configure multi-channel alerts
- [ ] Add monitoring dashboards

### Week 3: Advanced Workflows
- [ ] Set up Temporal server
- [ ] Implement monthly billing workflow
- [ ] Add workflow monitoring
- [ ] Migrate complex processes to Temporal

### Week 4: Performance & Reliability
- [ ] Add fastapi-limiter for budget enforcement
- [ ] Implement distributed rate limiting
- [ ] Add circuit breakers for external services
- [ ] Performance testing and optimization

### Week 5-6: Advanced Features
- [ ] Integrate OpenMeter for advanced usage tracking
- [ ] Add real-time usage aggregation
- [ ] Implement advanced billing features
- [ ] Add comprehensive monitoring and alerting

## Benefits Summary

| Library | Primary Benefit | Implementation Effort | Impact |
|---------|----------------|---------------------|---------|
| Celery | Reliable async processing | Low | High |
| APScheduler | Automated monitoring | Low | Medium |
| Apprise | Multi-channel alerts | Low | Medium |
| Temporal | Guaranteed workflows | Medium | High |
| fastapi-limiter | Real-time enforcement | Low | Medium |
| OpenMeter | Advanced metering | Medium | High |

This enhancement plan transforms our billing system from a basic implementation to a production-ready, enterprise-grade solution with minimal additional complexity.
