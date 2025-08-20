"""
Usage orchestrator service.

This service coordinates usage tracking, cost calculation, budget enforcement,
and reporting by orchestrating multiple smaller services.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio

from app.services.budget.budget_enforcement_service import BudgetEnforcementService, BudgetExceededException
from app.services.usage.cost_calculation_service import CostCalculationService, UsageCost
from app.services.billing.subscription_service import SubscriptionService
from app.services.payment.factory import get_payment_provider
from app.services.payment.protocol import PaymentProvider
from app.db import models
import logging
import uuid

logger = logging.getLogger(__name__)


class UsageOrchestrator:
    """
    Orchestrator for usage tracking and budget enforcement.
    
    This service coordinates usage recording, cost calculation,
    budget enforcement, and payment provider reporting.
    """
    
    def __init__(self, db: Session, payment_provider: Optional[PaymentProvider] = None):
        self.db = db
        self.payment_provider = payment_provider or get_payment_provider()
        
        # Initialize component services
        self.budget_enforcement = BudgetEnforcementService(db)
        self.cost_calculator = CostCalculationService()
        self.subscription_service = SubscriptionService(db, self.payment_provider)
    
    async def record_agent_invocation(
        self,
        org_id: str,
        agent_id: str,
        run_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[models.UsageRecord]:
        """
        Record usage for an agent invocation with budget enforcement.
        
        Args:
            org_id: Organization ID
            agent_id: Agent ID
            run_id: Run ID
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            metadata: Additional metadata
            
        Returns:
            List of created usage records
            
        Raises:
            BudgetExceededException: If budget limits would be exceeded
        """
        # Calculate costs for different usage types
        usage_costs = self.cost_calculator.calculate_invocation_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            org_id=org_id
        )
        
        # Check budget before recording usage
        total_cost_cents = self.cost_calculator.calculate_total_cost(usage_costs)
        self.budget_enforcement.check_budget_before_usage(org_id, total_cost_cents, agent_id)
        
        # Record each usage type
        usage_records = []
        for cost in usage_costs:
            if cost.quantity > 0:  # Only record non-zero usage
                usage_record = self._create_usage_record(
                    org_id=org_id,
                    agent_id=agent_id,
                    run_id=run_id,
                    usage_cost=cost,
                    metadata={
                        **(metadata or {}),
                        "rate_cents_per_unit": cost.rate_cents_per_unit
                    }
                )
                usage_records.append(usage_record)
        
        # Update budgets
        self.budget_enforcement.update_budgets_for_usage(org_id, total_cost_cents, agent_id)
        
        # Report usage to payment provider (async)
        asyncio.create_task(self._report_usage_to_provider(org_id, total_cost_cents))
        
        logger.info(f"Recorded invocation usage for agent {agent_id}: ${total_cost_cents/100:.2f}")
        return usage_records
    
    async def record_learning_usage(
        self,
        org_id: str,
        agent_id: str,
        learning_hours: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> models.UsageRecord:
        """Record usage for agent learning/training"""
        # Convert hours to centihours for more precise calculation
        quantity = int(learning_hours * 100)
        cost = self.cost_calculator.calculate_cost("learning_hour", quantity, org_id)
        
        # Check budget
        self.budget_enforcement.check_budget_before_usage(org_id, cost.cost_cents, agent_id)
        
        # Record usage
        usage_record = self._create_usage_record(
            org_id=org_id,
            agent_id=agent_id,
            run_id=None,
            usage_cost=cost,
            metadata={
                **(metadata or {}),
                "learning_hours": learning_hours,
                "rate_cents_per_unit": cost.rate_cents_per_unit
            }
        )
        
        # Update budgets
        self.budget_enforcement.update_budgets_for_usage(org_id, cost.cost_cents, agent_id)
        
        # Report to payment provider
        asyncio.create_task(self._report_usage_to_provider(org_id, cost.cost_cents))
        
        logger.info(f"Recorded learning usage for agent {agent_id}: {learning_hours} hours, ${cost.cost_cents/100:.2f}")
        return usage_record
    
    async def record_storage_usage(
        self,
        org_id: str,
        storage_mb: int,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> models.UsageRecord:
        """Record storage usage (typically monthly)"""
        cost = self.cost_calculator.calculate_cost("storage_mb", storage_mb, org_id)
        
        # Check budget
        self.budget_enforcement.check_budget_before_usage(org_id, cost.cost_cents, agent_id)
        
        # Record usage
        usage_record = self._create_usage_record(
            org_id=org_id,
            agent_id=agent_id,
            run_id=None,
            usage_cost=cost,
            metadata={
                **(metadata or {}),
                "storage_mb": storage_mb,
                "rate_cents_per_unit": cost.rate_cents_per_unit
            }
        )
        
        # Update budgets
        self.budget_enforcement.update_budgets_for_usage(org_id, cost.cost_cents, agent_id)
        
        # Report to payment provider
        asyncio.create_task(self._report_usage_to_provider(org_id, cost.cost_cents))
        
        logger.info(f"Recorded storage usage for org {org_id}: {storage_mb} MB, ${cost.cost_cents/100:.2f}")
        return usage_record
    
    def check_budget_before_invocation(
        self,
        org_id: str,
        agent_id: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> bool:
        """
        Check if an invocation would exceed budget limits.
        
        Args:
            org_id: Organization ID
            agent_id: Agent ID
            estimated_input_tokens: Estimated input tokens
            estimated_output_tokens: Estimated output tokens
            
        Returns:
            True if invocation is allowed
            
        Raises:
            BudgetExceededException: If budget would be exceeded
        """
        estimated_cost = self.cost_calculator.estimate_invocation_cost(
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            org_id=org_id
        )
        
        return self.budget_enforcement.check_budget_before_usage(
            org_id=org_id,
            estimated_cost_cents=estimated_cost,
            agent_id=agent_id
        )
    
    def get_usage_summary(
        self,
        org_id: str,
        agent_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage summary for an organization or agent"""
        query = self.db.query(models.UsageRecord).filter(models.UsageRecord.org_id == org_id)
        
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
                    "count": 0
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
            "period_end": period_end.isoformat() if period_end else None
        }
    
    def get_budget_status(self, org_id: str) -> Dict[str, Any]:
        """Get budget status and warnings for an organization"""
        # Get budget violations
        violations = self.budget_enforcement.get_budget_violations(org_id)
        
        # Get budget warnings
        warnings = self.budget_enforcement.get_budget_warnings(org_id)
        
        return {
            "violations": [
                {
                    "budget_id": budget.id,
                    "agent_id": budget.agent_id,
                    "period": budget.period,
                    "limit_cents": budget.limit_cents,
                    "current_usage_cents": budget.current_usage_cents,
                    "enforcement_mode": budget.enforcement_mode
                }
                for budget in violations
            ],
            "warnings": warnings,
            "has_violations": len(violations) > 0,
            "has_warnings": len(warnings) > 0
        }
    
    # Private helper methods
    
    def _create_usage_record(
        self,
        org_id: str,
        usage_cost: UsageCost,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> models.UsageRecord:
        """Create and save a usage record"""
        now = datetime.utcnow()
        billing_period = now.strftime("%Y-%m")  # YYYY-MM format
        
        usage_record = models.UsageRecord(
            id=str(uuid.uuid4()),
            org_id=org_id,
            agent_id=agent_id,
            run_id=run_id,
            usage_type=usage_cost.usage_type,
            quantity=usage_cost.quantity,
            cost_cents=usage_cost.cost_cents,
            recorded_at=now,
            billing_period=billing_period,
            metadata=metadata or {}
        )
        
        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)
        
        return usage_record
    
    async def _report_usage_to_provider(self, org_id: str, cost_cents: int):
        """Report usage to payment provider for billing"""
        try:
            # Get subscription usage item ID
            usage_item_id = await self.subscription_service.get_subscription_usage_item_id(org_id)
            if not usage_item_id:
                logger.debug(f"No usage item ID found for org {org_id}")
                return
            
            # Report usage to payment provider
            success = await self.payment_provider.create_usage_record(
                subscription_item_id=usage_item_id,
                quantity=cost_cents  # Report in cents
            )
            
            if success:
                logger.info(f"Reported usage to payment provider: {cost_cents} cents for org {org_id}")
            else:
                logger.warning(f"Failed to report usage to payment provider for org {org_id}")
                
        except Exception as e:
            logger.error(f"Error reporting usage for org {org_id}: {e}")
