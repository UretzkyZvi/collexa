"""
Budget service for managing spending limits and enforcement.

This service handles budget creation, usage tracking, enforcement,
and alerting for organizations and individual agents.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from enum import Enum

from app.db import models
from app.core.config import settings
import logging
import uuid

logger = logging.getLogger(__name__)


class BudgetPeriod(Enum):
    """Budget period types"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class EnforcementMode(Enum):
    """Budget enforcement modes"""

    SOFT = "soft"  # Warn but allow
    HARD = "hard"  # Block when exceeded


class BudgetStatus(Enum):
    """Budget status"""

    ACTIVE = "active"
    EXCEEDED = "exceeded"
    DISABLED = "disabled"


class BudgetExceededException(Exception):
    """Raised when a hard budget limit is exceeded"""

    def __init__(self, budget_id: str, limit_cents: int, current_usage_cents: int):
        self.budget_id = budget_id
        self.limit_cents = limit_cents
        self.current_usage_cents = current_usage_cents
        super().__init__(
            f"Budget {budget_id} exceeded: {current_usage_cents} > {limit_cents} cents"
        )


class BudgetService:
    """Service for managing budgets and usage tracking"""

    def __init__(self, db: Session):
        self.db = db

    def create_budget(
        self,
        org_id: str,
        period: BudgetPeriod,
        limit_cents: int,
        agent_id: Optional[str] = None,
        enforcement_mode: EnforcementMode = EnforcementMode.SOFT,
        alerts_config: Optional[Dict[str, Any]] = None,
    ) -> models.Budget:
        """
        Create a new budget for an organization or agent.

        Args:
            org_id: Organization ID
            period: Budget period (daily, weekly, monthly)
            limit_cents: Budget limit in cents
            agent_id: Agent ID (None for org-level budget)
            enforcement_mode: How to enforce the budget
            alerts_config: Alert configuration

        Returns:
            Created Budget model
        """
        # Calculate period start and end
        now = datetime.utcnow()
        period_start, period_end = self._calculate_period_bounds(now, period)

        # Default alerts configuration
        if alerts_config is None:
            alerts_config = {
                "thresholds": [50, 80, 95],  # Alert at 50%, 80%, 95%
                "channels": ["email"],  # Alert channels
                "enabled": True,
            }

        budget = models.Budget(
            id=str(uuid.uuid4()),
            org_id=org_id,
            agent_id=agent_id,
            period=period.value,
            limit_cents=limit_cents,
            current_usage_cents=0,
            period_start=period_start,
            period_end=period_end,
            alerts_json=alerts_config,
            enforcement_mode=enforcement_mode.value,
            status=BudgetStatus.ACTIVE.value,
        )

        self.db.add(budget)
        self.db.commit()
        self.db.refresh(budget)

        logger.info(f"Created budget {budget.id} for org {org_id}, agent {agent_id}")
        return budget

    def get_budget(self, budget_id: str) -> Optional[models.Budget]:
        """Get budget by ID"""
        return (
            self.db.query(models.Budget).filter(models.Budget.id == budget_id).first()
        )

    def get_budgets_for_org(
        self, org_id: str, agent_id: Optional[str] = None
    ) -> List[models.Budget]:
        """Get all budgets for an organization, optionally filtered by agent"""
        query = self.db.query(models.Budget).filter(models.Budget.org_id == org_id)

        if agent_id is not None:
            query = query.filter(models.Budget.agent_id == agent_id)

        return query.all()

    def record_usage(
        self,
        org_id: str,
        usage_type: str,
        quantity: int,
        cost_cents: int,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> models.UsageRecord:
        """
        Record usage and update relevant budgets.

        Args:
            org_id: Organization ID
            usage_type: Type of usage (invocation, tokens, storage)
            quantity: Number of units used
            cost_cents: Cost in cents
            agent_id: Agent ID (if applicable)
            run_id: Run ID (if applicable)
            metadata: Additional metadata

        Returns:
            Created UsageRecord

        Raises:
            BudgetExceededException: If hard budget limit is exceeded
        """
        # Create usage record
        now = datetime.utcnow()
        billing_period = now.strftime("%Y-%m")  # YYYY-MM format

        usage_record = models.UsageRecord(
            id=str(uuid.uuid4()),
            org_id=org_id,
            agent_id=agent_id,
            run_id=run_id,
            usage_type=usage_type,
            quantity=quantity,
            cost_cents=cost_cents,
            recorded_at=now,
            billing_period=billing_period,
            metadata_json=metadata or {},
        )

        self.db.add(usage_record)

        # Update relevant budgets
        self._update_budgets_for_usage(org_id, agent_id, cost_cents, now)

        self.db.commit()
        self.db.refresh(usage_record)

        logger.info(
            f"Recorded usage: {usage_type} {quantity} units, ${cost_cents/100:.2f} for org {org_id}"
        )
        return usage_record

    def check_budget_before_usage(
        self, org_id: str, estimated_cost_cents: int, agent_id: Optional[str] = None
    ) -> bool:
        """
        Check if usage would exceed budget limits.

        Args:
            org_id: Organization ID
            estimated_cost_cents: Estimated cost of the operation
            agent_id: Agent ID (if applicable)

        Returns:
            True if usage is allowed, False if blocked by hard budget

        Raises:
            BudgetExceededException: If hard budget would be exceeded
        """
        now = datetime.utcnow()

        # Check agent-level budget first (if applicable)
        if agent_id:
            agent_budgets = self._get_active_budgets(org_id, agent_id, now)
            for budget in agent_budgets:
                if self._would_exceed_budget(budget, estimated_cost_cents):
                    if budget.enforcement_mode == EnforcementMode.HARD.value:
                        raise BudgetExceededException(
                            budget.id,
                            budget.limit_cents,
                            budget.current_usage_cents + estimated_cost_cents,
                        )

        # Check org-level budgets
        org_budgets = self._get_active_budgets(org_id, None, now)
        for budget in org_budgets:
            if self._would_exceed_budget(budget, estimated_cost_cents):
                if budget.enforcement_mode == EnforcementMode.HARD.value:
                    raise BudgetExceededException(
                        budget.id,
                        budget.limit_cents,
                        budget.current_usage_cents + estimated_cost_cents,
                    )

        return True

    def update_budget(
        self,
        budget_id: str,
        limit_cents: Optional[int] = None,
        enforcement_mode: Optional[EnforcementMode] = None,
        alerts_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[models.Budget]:
        """Update budget settings"""
        budget = self.get_budget(budget_id)
        if not budget:
            return None

        if limit_cents is not None:
            budget.limit_cents = limit_cents

        if enforcement_mode is not None:
            budget.enforcement_mode = enforcement_mode.value

        if alerts_config is not None:
            budget.alerts_json = alerts_config

        budget.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Updated budget {budget_id}")
        return budget

    def get_usage_summary(
        self,
        org_id: str,
        agent_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage summary for an organization or agent"""
        query = self.db.query(models.UsageRecord).filter(
            models.UsageRecord.org_id == org_id
        )

        if agent_id:
            query = query.filter(models.UsageRecord.agent_id == agent_id)

        if period_start:
            query = query.filter(models.UsageRecord.recorded_at >= period_start)

        if period_end:
            query = query.filter(models.UsageRecord.recorded_at <= period_end)

        usage_records = query.all()

        # Aggregate usage by type
        usage_by_type = {}
        total_cost_cents = 0

        for record in usage_records:
            if record.usage_type not in usage_by_type:
                usage_by_type[record.usage_type] = {
                    "quantity": 0,
                    "cost_cents": 0,
                    "count": 0,
                }

            usage_by_type[record.usage_type]["quantity"] += record.quantity
            usage_by_type[record.usage_type]["cost_cents"] += record.cost_cents
            usage_by_type[record.usage_type]["count"] += 1
            total_cost_cents += record.cost_cents

        return {
            "total_cost_cents": total_cost_cents,
            "total_cost_dollars": total_cost_cents / 100,
            "usage_by_type": usage_by_type,
            "record_count": len(usage_records),
            "period_start": period_start.isoformat() if period_start else None,
            "period_end": period_end.isoformat() if period_end else None,
        }

    # Private helper methods

    def _calculate_period_bounds(
        self, now: datetime, period: BudgetPeriod
    ) -> tuple[datetime, datetime]:
        """Calculate period start and end dates"""
        if period == BudgetPeriod.DAILY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period == BudgetPeriod.WEEKLY:
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(weeks=1)
        elif period == BudgetPeriod.MONTHLY:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)
        else:
            raise ValueError(f"Unsupported period: {period}")

        return start, end

    def _get_active_budgets(
        self, org_id: str, agent_id: Optional[str], now: datetime
    ) -> List[models.Budget]:
        """Get active budgets for the current period"""
        query = self.db.query(models.Budget).filter(
            and_(
                models.Budget.org_id == org_id,
                models.Budget.agent_id == agent_id,
                models.Budget.status == BudgetStatus.ACTIVE.value,
                models.Budget.period_start <= now,
                models.Budget.period_end > now,
            )
        )
        return query.all()

    def _would_exceed_budget(
        self, budget: models.Budget, additional_cost_cents: int
    ) -> bool:
        """Check if additional cost would exceed budget"""
        return (budget.current_usage_cents + additional_cost_cents) > budget.limit_cents

    def _update_budgets_for_usage(
        self, org_id: str, agent_id: Optional[str], cost_cents: int, now: datetime
    ):
        """Update budget usage counters"""
        # Update agent-level budgets
        if agent_id:
            agent_budgets = self._get_active_budgets(org_id, agent_id, now)
            for budget in agent_budgets:
                budget.current_usage_cents += cost_cents
                if budget.current_usage_cents > budget.limit_cents:
                    budget.status = BudgetStatus.EXCEEDED.value

        # Update org-level budgets
        org_budgets = self._get_active_budgets(org_id, None, now)
        for budget in org_budgets:
            budget.current_usage_cents += cost_cents
            if budget.current_usage_cents > budget.limit_cents:
                budget.status = BudgetStatus.EXCEEDED.value
