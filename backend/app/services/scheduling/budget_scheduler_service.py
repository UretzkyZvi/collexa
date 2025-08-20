"""
Budget scheduler service using APScheduler.

This service provides automated budget monitoring, period resets,
and scheduled maintenance tasks for the billing system.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import asyncio

from app.services.budget.budget_enforcement_service import BudgetEnforcementService
from app.services.usage_orchestrator import UsageOrchestrator
from app.services.budget_service import BudgetService, BudgetPeriod
from app.db.session import get_db
from app.db import models
from app.core.config import settings

logger = logging.getLogger(__name__)


# Module-level job wrapper functions to avoid APScheduler serialization of instance methods
# These wrappers are importable and do not close over unserializable state.
async def job_check_budget_violations():
    from app.services.scheduling.budget_scheduler_service import budget_scheduler
    await budget_scheduler.check_budget_violations()

async def job_check_budget_warnings():
    from app.services.scheduling.budget_scheduler_service import budget_scheduler
    await budget_scheduler.check_budget_warnings()

async def job_reset_daily_budgets():
    from app.services.scheduling.budget_scheduler_service import budget_scheduler
    await budget_scheduler.reset_daily_budgets()

async def job_reset_weekly_budgets():
    from app.services.scheduling.budget_scheduler_service import budget_scheduler
    await budget_scheduler.reset_weekly_budgets()

async def job_reset_monthly_budgets():
    from app.services.scheduling.budget_scheduler_service import budget_scheduler
    await budget_scheduler.reset_monthly_budgets()

async def job_generate_monthly_reports():
    from app.services.scheduling.budget_scheduler_service import budget_scheduler
    await budget_scheduler.generate_monthly_reports()

async def job_cleanup_old_usage_records():
    from app.services.scheduling.budget_scheduler_service import budget_scheduler
    await budget_scheduler.cleanup_old_usage_records()


class BudgetSchedulerService:
    """Service for automated budget monitoring and maintenance"""

    def __init__(self):
        # Configure job stores and executors
        jobstores = {
            'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
        }
        executors = {
            'default': AsyncIOExecutor()
        }

        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 300  # 5 minutes
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        self.setup_jobs()

    def setup_jobs(self):
        """Setup all scheduled jobs"""

        # Budget violation monitoring - every 15 minutes
        self.scheduler.add_job(
            func=job_check_budget_violations,
            trigger=IntervalTrigger(minutes=15),
            id='budget_violation_check',
            name='Check Budget Violations',
            replace_existing=True
        )

        # Budget warnings - every hour
        self.scheduler.add_job(
            func=job_check_budget_warnings,
            trigger=IntervalTrigger(hours=1),
            id='budget_warning_check',
            name='Check Budget Warnings',
            replace_existing=True
        )

        # Daily budget resets - at midnight UTC
        self.scheduler.add_job(
            func=job_reset_daily_budgets,
            trigger=CronTrigger(hour=0, minute=0),
            id='daily_budget_reset',
            name='Reset Daily Budgets',
            replace_existing=True
        )

        # Weekly budget resets - Monday at midnight UTC
        self.scheduler.add_job(
            func=job_reset_weekly_budgets,
            trigger=CronTrigger(day_of_week=0, hour=0, minute=0),
            id='weekly_budget_reset',
            name='Reset Weekly Budgets',
            replace_existing=True
        )

        # Monthly budget resets - 1st of month at midnight UTC
        self.scheduler.add_job(
            func=job_reset_monthly_budgets,
            trigger=CronTrigger(day=1, hour=0, minute=0),
            id='monthly_budget_reset',
            name='Reset Monthly Budgets',
            replace_existing=True
        )

        # Generate monthly usage reports - 2nd of month at 2 AM UTC
        self.scheduler.add_job(
            func=job_generate_monthly_reports,
            trigger=CronTrigger(day=2, hour=2, minute=0),
            id='monthly_usage_reports',
            name='Generate Monthly Usage Reports',
            replace_existing=True
        )

        # Cleanup old usage records - weekly on Sunday at 3 AM UTC
        self.scheduler.add_job(
            func=job_cleanup_old_usage_records,
            trigger=CronTrigger(day_of_week=6, hour=3, minute=0),
            id='cleanup_usage_records',
            name='Cleanup Old Usage Records',
            replace_existing=True
        )

        logger.info("Scheduled jobs configured successfully")

    async def start(self):
        """Start the scheduler"""
        try:
            self.scheduler.start()
            logger.info("Budget scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start budget scheduler: {e}")
            raise

    async def stop(self):
        """Stop the scheduler"""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Budget scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop budget scheduler: {e}")

    async def check_budget_violations(self):
        """Check for budget violations across all organizations"""
        try:
            db = next(get_db())
            budget_enforcement = BudgetEnforcementService(db)

            # Get all active organizations
            orgs = db.query(models.Org).all()

            violation_count = 0
            for org in orgs:
                violations = budget_enforcement.get_budget_violations(org.id)

                if violations:
                    violation_count += len(violations)
                    await self._handle_budget_violations(org.id, violations)

            logger.info(f"Budget violation check completed: {violation_count} violations found across {len(orgs)} organizations")

        except Exception as e:
            logger.error(f"Error checking budget violations: {e}")

    async def check_budget_warnings(self):
        """Check for budget warnings (approaching limits)"""
        try:
            db = next(get_db())
            budget_enforcement = BudgetEnforcementService(db)

            # Get all active organizations
            orgs = db.query(models.Org).all()

            warning_count = 0
            for org in orgs:
                warnings = budget_enforcement.get_budget_warnings(org.id, warning_threshold=0.8)

                if warnings:
                    warning_count += len(warnings)
                    await self._handle_budget_warnings(org.id, warnings)

            logger.info(f"Budget warning check completed: {warning_count} warnings found across {len(orgs)} organizations")

        except Exception as e:
            logger.error(f"Error checking budget warnings: {e}")

    async def reset_daily_budgets(self):
        """Reset all daily budgets"""
        await self._reset_budgets_by_period(BudgetPeriod.DAILY)

    async def reset_weekly_budgets(self):
        """Reset all weekly budgets"""
        await self._reset_budgets_by_period(BudgetPeriod.WEEKLY)

    async def reset_monthly_budgets(self):
        """Reset all monthly budgets"""
        await self._reset_budgets_by_period(BudgetPeriod.MONTHLY)

    async def generate_monthly_reports(self):
        """Generate monthly usage reports for all organizations"""
        try:
            db = next(get_db())
            usage_orchestrator = UsageOrchestrator(db)

            # Get previous month
            now = datetime.utcnow()
            if now.month == 1:
                prev_month = 12
                prev_year = now.year - 1
            else:
                prev_month = now.month - 1
                prev_year = now.year

            start_date = datetime(prev_year, prev_month, 1)
            if prev_month == 12:
                end_date = datetime(prev_year + 1, 1, 1)
            else:
                end_date = datetime(prev_year, prev_month + 1, 1)

            # Get all organizations
            orgs = db.query(models.Org).all()

            for org in orgs:
                try:
                    # Generate report
                    report = await usage_orchestrator.generate_usage_report(
                        org.id, start_date, end_date
                    )

                    # TODO: Store report or send via email
                    logger.info(f"Generated monthly report for org {org.id}: ${report['summary']['total_cost_dollars']:.2f}")

                except Exception as e:
                    logger.error(f"Failed to generate monthly report for org {org.id}: {e}")

            logger.info(f"Monthly report generation completed for {len(orgs)} organizations")

        except Exception as e:
            logger.error(f"Error generating monthly reports: {e}")

    async def cleanup_old_usage_records(self):
        """Cleanup usage records older than 2 years"""
        try:
            db = next(get_db())

            # Delete usage records older than 2 years
            cutoff_date = datetime.utcnow() - timedelta(days=730)

            deleted_count = db.query(models.UsageRecord).filter(
                models.UsageRecord.recorded_at < cutoff_date
            ).delete()

            db.commit()

            logger.info(f"Cleanup completed: deleted {deleted_count} old usage records")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            db.rollback()

    # Private helper methods

    async def _reset_budgets_by_period(self, period: BudgetPeriod):
        """Reset budgets for a specific period"""
        try:
            db = next(get_db())
            budget_enforcement = BudgetEnforcementService(db)

            # Get all budgets for this period
            budgets = db.query(models.Budget).filter(
                models.Budget.period == period.value
            ).all()

            reset_count = 0
            for budget in budgets:
                try:
                    budget_enforcement.reset_budget_period(budget.id)
                    reset_count += 1
                except Exception as e:
                    logger.error(f"Failed to reset budget {budget.id}: {e}")

            logger.info(f"Reset {reset_count} {period.value} budgets")

        except Exception as e:
            logger.error(f"Error resetting {period.value} budgets: {e}")

    async def _handle_budget_violations(self, org_id: str, violations: List[models.Budget]):
        """Handle budget violations by sending alerts"""
        try:
            # Queue alert tasks
            from app.services.billing.async_webhook_service import send_budget_alert_async

            for violation in violations:
                alert_data = {
                    "budget_id": violation.id,
                    "budget_name": f"{'Agent' if violation.agent_id else 'Organization'} {violation.period} budget",
                    "agent_id": violation.agent_id,
                    "limit_cents": violation.limit_cents,
                    "current_usage_cents": violation.current_usage_cents,
                    "utilization_percent": (violation.current_usage_cents / violation.limit_cents * 100) if violation.limit_cents > 0 else 0,
                    "enforcement_mode": violation.enforcement_mode,
                    "period_end": violation.period_end.isoformat()
                }

                # Queue async alert
                send_budget_alert_async.delay(org_id, "violation", alert_data)

            logger.info(f"Queued {len(violations)} violation alerts for org {org_id}")

        except Exception as e:
            logger.error(f"Error handling budget violations for org {org_id}: {e}")

    async def _handle_budget_warnings(self, org_id: str, warnings: List[Dict[str, Any]]):
        """Handle budget warnings by sending alerts"""
        try:
            # Queue alert task
            from app.services.billing.async_webhook_service import send_budget_alert_async

            send_budget_alert_async.delay(org_id, "warning", {"warnings": warnings})

            logger.info(f"Queued warning alert for org {org_id} with {len(warnings)} warnings")

        except Exception as e:
            logger.error(f"Error handling budget warnings for org {org_id}: {e}")

    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })

        return {
            "scheduler_running": self.scheduler.running,
            "job_count": len(jobs),
            "jobs": jobs
        }


# Global scheduler instance
budget_scheduler = BudgetSchedulerService()
