"""
Budget enforcement service.

This service handles budget validation, enforcement, and alerting
to ensure spending limits are respected.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from enum import Enum

from app.db import models
import logging

logger = logging.getLogger(__name__)


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
        super().__init__(f"Budget {budget_id} exceeded: {current_usage_cents} > {limit_cents} cents")


class BudgetEnforcementService:
    """Service for budget enforcement and validation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_budget_before_usage(
        self,
        org_id: str,
        estimated_cost_cents: int,
        agent_id: Optional[str] = None
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
                            budget.current_usage_cents + estimated_cost_cents
                        )
                    else:
                        logger.warning(f"Soft budget limit exceeded for budget {budget.id}")
        
        # Check org-level budgets
        org_budgets = self._get_active_budgets(org_id, None, now)
        for budget in org_budgets:
            if self._would_exceed_budget(budget, estimated_cost_cents):
                if budget.enforcement_mode == EnforcementMode.HARD.value:
                    raise BudgetExceededException(
                        budget.id, 
                        budget.limit_cents, 
                        budget.current_usage_cents + estimated_cost_cents
                    )
                else:
                    logger.warning(f"Soft budget limit exceeded for budget {budget.id}")
        
        return True
    
    def update_budgets_for_usage(
        self,
        org_id: str,
        cost_cents: int,
        agent_id: Optional[str] = None
    ) -> List[models.Budget]:
        """
        Update budget usage counters after usage is recorded.
        
        Args:
            org_id: Organization ID
            cost_cents: Cost in cents to add to budgets
            agent_id: Agent ID (if applicable)
            
        Returns:
            List of updated budgets
        """
        now = datetime.utcnow()
        updated_budgets = []
        
        # Update agent-level budgets
        if agent_id:
            agent_budgets = self._get_active_budgets(org_id, agent_id, now)
            for budget in agent_budgets:
                budget.current_usage_cents += cost_cents
                if budget.current_usage_cents > budget.limit_cents:
                    budget.status = BudgetStatus.EXCEEDED.value
                updated_budgets.append(budget)
        
        # Update org-level budgets
        org_budgets = self._get_active_budgets(org_id, None, now)
        for budget in org_budgets:
            budget.current_usage_cents += cost_cents
            if budget.current_usage_cents > budget.limit_cents:
                budget.status = BudgetStatus.EXCEEDED.value
            updated_budgets.append(budget)
        
        if updated_budgets:
            self.db.commit()
            logger.info(f"Updated {len(updated_budgets)} budgets for org {org_id}")
        
        return updated_budgets
    
    def get_budget_violations(
        self,
        org_id: str,
        agent_id: Optional[str] = None
    ) -> List[models.Budget]:
        """
        Get budgets that are currently exceeded.
        
        Args:
            org_id: Organization ID
            agent_id: Agent ID (optional filter)
            
        Returns:
            List of exceeded budgets
        """
        query = self.db.query(models.Budget).filter(
            and_(
                models.Budget.org_id == org_id,
                models.Budget.status == BudgetStatus.EXCEEDED.value
            )
        )
        
        if agent_id is not None:
            query = query.filter(models.Budget.agent_id == agent_id)
        
        return query.all()
    
    def get_budget_warnings(
        self,
        org_id: str,
        warning_threshold: float = 0.8,
        agent_id: Optional[str] = None
    ) -> List[dict]:
        """
        Get budgets that are approaching their limits.
        
        Args:
            org_id: Organization ID
            warning_threshold: Threshold percentage (0.8 = 80%)
            agent_id: Agent ID (optional filter)
            
        Returns:
            List of budget warning information
        """
        now = datetime.utcnow()
        budgets = self._get_active_budgets(org_id, agent_id, now)
        
        warnings = []
        for budget in budgets:
            if budget.limit_cents > 0:
                utilization = budget.current_usage_cents / budget.limit_cents
                if utilization >= warning_threshold and budget.status != BudgetStatus.EXCEEDED.value:
                    warnings.append({
                        "budget_id": budget.id,
                        "budget_name": f"{'Agent' if budget.agent_id else 'Organization'} {budget.period} budget",
                        "agent_id": budget.agent_id,
                        "utilization_percent": utilization * 100,
                        "current_usage_cents": budget.current_usage_cents,
                        "limit_cents": budget.limit_cents,
                        "remaining_cents": budget.limit_cents - budget.current_usage_cents,
                        "enforcement_mode": budget.enforcement_mode
                    })
        
        return warnings
    
    def reset_budget_period(self, budget_id: str) -> Optional[models.Budget]:
        """
        Reset budget usage for a new period.
        
        Args:
            budget_id: Budget ID to reset
            
        Returns:
            Updated budget or None if not found
        """
        budget = self.db.query(models.Budget).filter(models.Budget.id == budget_id).first()
        if not budget:
            return None
        
        # Reset usage and status
        budget.current_usage_cents = 0
        budget.status = BudgetStatus.ACTIVE.value
        
        # Update period dates based on budget period
        from app.services.budget_service import BudgetPeriod
        from datetime import timedelta
        
        now = datetime.utcnow()
        if budget.period == BudgetPeriod.DAILY.value:
            budget.period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            budget.period_end = budget.period_start + timedelta(days=1)
        elif budget.period == BudgetPeriod.WEEKLY.value:
            days_since_monday = now.weekday()
            budget.period_start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            budget.period_end = budget.period_start + timedelta(weeks=1)
        elif budget.period == BudgetPeriod.MONTHLY.value:
            budget.period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if budget.period_start.month == 12:
                budget.period_end = budget.period_start.replace(year=budget.period_start.year + 1, month=1)
            else:
                budget.period_end = budget.period_start.replace(month=budget.period_start.month + 1)
        
        budget.updated_at = now
        self.db.commit()
        
        logger.info(f"Reset budget period for budget {budget_id}")
        return budget
    
    def disable_budget(self, budget_id: str) -> Optional[models.Budget]:
        """
        Disable a budget (stops enforcement).
        
        Args:
            budget_id: Budget ID to disable
            
        Returns:
            Updated budget or None if not found
        """
        budget = self.db.query(models.Budget).filter(models.Budget.id == budget_id).first()
        if not budget:
            return None
        
        budget.status = BudgetStatus.DISABLED.value
        budget.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Disabled budget {budget_id}")
        return budget
    
    def enable_budget(self, budget_id: str) -> Optional[models.Budget]:
        """
        Enable a disabled budget.
        
        Args:
            budget_id: Budget ID to enable
            
        Returns:
            Updated budget or None if not found
        """
        budget = self.db.query(models.Budget).filter(models.Budget.id == budget_id).first()
        if not budget:
            return None
        
        # Determine status based on current usage
        if budget.current_usage_cents > budget.limit_cents:
            budget.status = BudgetStatus.EXCEEDED.value
        else:
            budget.status = BudgetStatus.ACTIVE.value
        
        budget.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Enabled budget {budget_id}")
        return budget
    
    # Private helper methods
    
    def _get_active_budgets(self, org_id: str, agent_id: Optional[str], now: datetime) -> List[models.Budget]:
        """Get active budgets for the current period"""
        query = self.db.query(models.Budget).filter(
            and_(
                models.Budget.org_id == org_id,
                models.Budget.agent_id == agent_id,
                models.Budget.status.in_([BudgetStatus.ACTIVE.value, BudgetStatus.EXCEEDED.value]),
                models.Budget.period_start <= now,
                models.Budget.period_end > now
            )
        )
        return query.all()
    
    def _would_exceed_budget(self, budget: models.Budget, additional_cost_cents: int) -> bool:
        """Check if additional cost would exceed budget"""
        return (budget.current_usage_cents + additional_cost_cents) > budget.limit_cents
