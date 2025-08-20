"""
Admin API endpoints for system management.

This module provides administrative endpoints for managing
the billing system, scheduler, and notifications.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.db.session import get_db
from app.middleware.auth_middleware import get_current_org_id
from app.services.scheduling.budget_scheduler_service import budget_scheduler
from app.services.notifications.alert_service import alert_service, AlertSeverity
from app.services.billing.async_webhook_service import celery_app
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class TestNotificationRequest(BaseModel):
    """Request model for testing notifications"""
    title: str
    message: str
    severity: str = "info"


class SystemAlertRequest(BaseModel):
    """Request model for sending system alerts"""
    title: str
    message: str
    severity: str = "info"
    metadata: Optional[Dict[str, Any]] = None


@router.get("/admin/scheduler/status")
async def get_scheduler_status():
    """Get status of the budget scheduler"""
    try:
        status = budget_scheduler.get_job_status()
        return {
            "scheduler": status,
            "timestamp": "2025-01-19T12:00:00Z"
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scheduler status")


@router.post("/admin/scheduler/start")
async def start_scheduler():
    """Start the budget scheduler"""
    try:
        await budget_scheduler.start()
        return {"status": "started", "message": "Budget scheduler started successfully"}
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/admin/scheduler/stop")
async def stop_scheduler():
    """Stop the budget scheduler"""
    try:
        await budget_scheduler.stop()
        return {"status": "stopped", "message": "Budget scheduler stopped successfully"}
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


@router.post("/admin/scheduler/jobs/{job_id}/run")
async def run_job_now(job_id: str):
    """Manually trigger a scheduled job"""
    try:
        job = budget_scheduler.scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Run the job immediately
        job.func()
        
        return {
            "status": "executed",
            "job_id": job_id,
            "message": f"Job {job_id} executed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run job: {str(e)}")


@router.get("/admin/notifications/channels")
async def get_notification_channels():
    """Get configured notification channels"""
    try:
        channels = alert_service.get_configured_channels()
        return {
            "channels": channels,
            "count": len(channels),
            "available_channels": ["email", "slack", "discord", "teams", "webhook"]
        }
    except Exception as e:
        logger.error(f"Error getting notification channels: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification channels")


@router.post("/admin/notifications/test")
async def test_notifications():
    """Test all configured notification channels"""
    try:
        result = await alert_service.test_notifications()
        return result
    except Exception as e:
        logger.error(f"Error testing notifications: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test notifications: {str(e)}")


@router.post("/admin/notifications/send")
async def send_system_alert(request: SystemAlertRequest):
    """Send a system alert through all configured channels"""
    try:
        # Validate severity
        try:
            severity = AlertSeverity(request.severity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {request.severity}")
        
        success = await alert_service.send_system_alert(
            title=request.title,
            message=request.message,
            severity=severity,
            metadata=request.metadata
        )
        
        if success:
            return {"status": "sent", "message": "System alert sent successfully"}
        else:
            return {"status": "failed", "message": "Failed to send system alert"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending system alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send system alert: {str(e)}")


@router.get("/admin/celery/status")
async def get_celery_status():
    """Get Celery worker and task status"""
    try:
        # Get active tasks
        active_tasks = celery_app.control.inspect().active()
        
        # Get scheduled tasks
        scheduled_tasks = celery_app.control.inspect().scheduled()
        
        # Get worker stats
        stats = celery_app.control.inspect().stats()
        
        return {
            "active_tasks": active_tasks,
            "scheduled_tasks": scheduled_tasks,
            "worker_stats": stats,
            "broker_url": celery_app.conf.broker_url,
            "result_backend": celery_app.conf.result_backend
        }
    except Exception as e:
        logger.error(f"Error getting Celery status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Celery status")


@router.get("/admin/celery/tasks")
async def list_celery_tasks():
    """List all registered Celery tasks"""
    try:
        tasks = list(celery_app.tasks.keys())
        return {
            "tasks": tasks,
            "count": len(tasks)
        }
    except Exception as e:
        logger.error(f"Error listing Celery tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list Celery tasks")


@router.post("/admin/budget/check-violations")
async def trigger_budget_check():
    """Manually trigger budget violation check"""
    try:
        from app.services.billing.async_webhook_service import check_budget_violations_async
        
        # Queue the task
        task = check_budget_violations_async.delay()
        
        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Budget violation check queued"
        }
    except Exception as e:
        logger.error(f"Error triggering budget check: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger budget check")


@router.post("/admin/reports/generate/{org_id}")
async def generate_monthly_report(org_id: str, month: str):
    """Generate monthly usage report for an organization"""
    try:
        from app.services.billing.async_webhook_service import generate_monthly_usage_report_async
        
        # Validate month format (YYYY-MM)
        try:
            year, month_num = month.split("-")
            int(year)
            int(month_num)
            if not (1 <= int(month_num) <= 12):
                raise ValueError("Invalid month")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
        
        # Queue the task
        task = generate_monthly_usage_report_async.delay(org_id, month)
        
        return {
            "status": "queued",
            "task_id": task.id,
            "org_id": org_id,
            "month": month,
            "message": "Monthly report generation queued"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating monthly report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate monthly report")


@router.get("/admin/system/health")
async def get_system_health():
    """Get overall system health status"""
    try:
        # Check scheduler
        scheduler_running = budget_scheduler.scheduler.running if budget_scheduler.scheduler else False
        
        # Check notification channels
        notification_channels = alert_service.get_configured_channels()
        
        # Check Celery (basic check)
        celery_healthy = True
        try:
            celery_app.control.inspect().ping()
        except Exception:
            celery_healthy = False
        
        # Overall health
        overall_healthy = scheduler_running and len(notification_channels) > 0 and celery_healthy
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "components": {
                "scheduler": {
                    "status": "running" if scheduler_running else "stopped",
                    "healthy": scheduler_running
                },
                "notifications": {
                    "status": f"{len(notification_channels)} channels configured",
                    "healthy": len(notification_channels) > 0,
                    "channels": notification_channels
                },
                "celery": {
                    "status": "running" if celery_healthy else "unavailable",
                    "healthy": celery_healthy
                }
            },
            "timestamp": "2025-01-19T12:00:00Z"
        }
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system health")
