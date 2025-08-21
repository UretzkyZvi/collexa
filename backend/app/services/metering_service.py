"""
Usage metering service for tracking and reporting usage to payment providers.

This service handles usage tracking, cost calculation, and reporting
to payment providers for billing purposes.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime
from dataclasses import dataclass

from app.services.billing_service import BillingService
from app.services.budget_service import BudgetService
from app.services.payment.protocol import PaymentProviderError
from app.db import models
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class UsageCost:
    """Usage cost calculation result"""

    usage_type: str
    quantity: int
    cost_cents: int
    rate_cents_per_unit: int


class MeteringService:
    """Service for usage metering and cost calculation"""

    # Default pricing rates (cents per unit)
    DEFAULT_RATES = {
        "invocation": 10,  # 10 cents per invocation
        "input_tokens": 1,  # 1 cent per 1000 input tokens
        "output_tokens": 2,  # 2 cents per 1000 output tokens
        "storage_mb": 5,  # 5 cents per MB per month
        "learning_hour": 100,  # $1 per learning hour
    }

    def __init__(self, db: Session):
        self.db = db
        self.budget_service = BudgetService(db)
        self.billing_service = BillingService(db)

    async def record_agent_invocation(
        self,
        org_id: str,
        agent_id: str,
        run_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[models.UsageRecord]:
        """
        Record usage for an agent invocation.

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
        usage_records = []

        # Calculate costs for different usage types
        costs = [
            self._calculate_cost("invocation", 1),
            self._calculate_cost("input_tokens", input_tokens),
            self._calculate_cost("output_tokens", output_tokens),
        ]

        # Check budget before recording usage
        total_cost_cents = sum(cost.cost_cents for cost in costs)
        self.budget_service.check_budget_before_usage(
            org_id, total_cost_cents, agent_id
        )

        # Record each usage type
        for cost in costs:
            if cost.quantity > 0:  # Only record non-zero usage
                usage_record = self.budget_service.record_usage(
                    org_id=org_id,
                    usage_type=cost.usage_type,
                    quantity=cost.quantity,
                    cost_cents=cost.cost_cents,
                    agent_id=agent_id,
                    run_id=run_id,
                    metadata={
                        **(metadata or {}),
                        "rate_cents_per_unit": cost.rate_cents_per_unit,
                    },
                )
                usage_records.append(usage_record)

        # Report usage to payment provider (async)
        asyncio.create_task(self._report_usage_to_provider(org_id, total_cost_cents))

        logger.info(
            f"Recorded invocation usage for agent {agent_id}: ${total_cost_cents/100:.2f}"
        )
        return usage_records

    async def record_learning_usage(
        self,
        org_id: str,
        agent_id: str,
        learning_hours: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> models.UsageRecord:
        """Record usage for agent learning/training"""
        cost = self._calculate_cost(
            "learning_hour", int(learning_hours * 100)
        )  # Convert to centihours

        # Check budget
        self.budget_service.check_budget_before_usage(org_id, cost.cost_cents, agent_id)

        # Record usage
        usage_record = self.budget_service.record_usage(
            org_id=org_id,
            usage_type=cost.usage_type,
            quantity=cost.quantity,
            cost_cents=cost.cost_cents,
            agent_id=agent_id,
            metadata={
                **(metadata or {}),
                "learning_hours": learning_hours,
                "rate_cents_per_unit": cost.rate_cents_per_unit,
            },
        )

        # Report to payment provider
        asyncio.create_task(self._report_usage_to_provider(org_id, cost.cost_cents))

        logger.info(
            f"Recorded learning usage for agent {agent_id}: {learning_hours} hours, ${cost.cost_cents/100:.2f}"
        )
        return usage_record

    async def record_storage_usage(
        self,
        org_id: str,
        storage_mb: int,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> models.UsageRecord:
        """Record storage usage (typically monthly)"""
        cost = self._calculate_cost("storage_mb", storage_mb)

        # Check budget
        self.budget_service.check_budget_before_usage(org_id, cost.cost_cents, agent_id)

        # Record usage
        usage_record = self.budget_service.record_usage(
            org_id=org_id,
            usage_type=cost.usage_type,
            quantity=cost.quantity,
            cost_cents=cost.cost_cents,
            agent_id=agent_id,
            metadata={
                **(metadata or {}),
                "storage_mb": storage_mb,
                "rate_cents_per_unit": cost.rate_cents_per_unit,
            },
        )

        # Report to payment provider
        asyncio.create_task(self._report_usage_to_provider(org_id, cost.cost_cents))

        logger.info(
            f"Recorded storage usage for org {org_id}: {storage_mb} MB, ${cost.cost_cents/100:.2f}"
        )
        return usage_record

    def get_usage_for_billing_period(
        self,
        org_id: str,
        billing_period: str,  # Format: "YYYY-MM"
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get usage summary for a billing period"""
        # Parse billing period
        year, month = billing_period.split("-")
        period_start = datetime(int(year), int(month), 1)

        # Calculate period end
        if int(month) == 12:
            period_end = datetime(int(year) + 1, 1, 1)
        else:
            period_end = datetime(int(year), int(month) + 1, 1)

        return self.budget_service.get_usage_summary(
            org_id=org_id,
            agent_id=agent_id,
            period_start=period_start,
            period_end=period_end,
        )

    def get_current_month_usage(
        self, org_id: str, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get usage for the current month"""
        now = datetime.utcnow()
        billing_period = now.strftime("%Y-%m")
        return self.get_usage_for_billing_period(org_id, billing_period, agent_id)

    async def generate_usage_report(
        self, org_id: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive usage report"""
        # Get overall usage summary
        summary = self.budget_service.get_usage_summary(
            org_id=org_id, period_start=start_date, period_end=end_date
        )

        # Get usage by agent
        agents_query = self.db.query(models.Agent).filter(models.Agent.org_id == org_id)
        agents = agents_query.all()

        agent_usage = {}
        for agent in agents:
            agent_summary = self.budget_service.get_usage_summary(
                org_id=org_id,
                agent_id=agent.id,
                period_start=start_date,
                period_end=end_date,
            )
            if agent_summary["record_count"] > 0:
                agent_usage[agent.id] = {
                    "agent_name": agent.display_name,
                    **agent_summary,
                }

        # Get budget status
        budgets = self.budget_service.get_budgets_for_org(org_id)
        budget_status = []
        for budget in budgets:
            budget_status.append(
                {
                    "budget_id": budget.id,
                    "agent_id": budget.agent_id,
                    "period": budget.period,
                    "limit_cents": budget.limit_cents,
                    "current_usage_cents": budget.current_usage_cents,
                    "utilization_percent": (
                        (budget.current_usage_cents / budget.limit_cents * 100)
                        if budget.limit_cents > 0
                        else 0
                    ),
                    "status": budget.status,
                    "enforcement_mode": budget.enforcement_mode,
                }
            )

        return {
            "org_id": org_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": summary,
            "agent_usage": agent_usage,
            "budget_status": budget_status,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # Private helper methods

    def _calculate_cost(self, usage_type: str, quantity: int) -> UsageCost:
        """Calculate cost for a usage type and quantity"""
        rate_cents_per_unit = self.DEFAULT_RATES.get(usage_type, 0)

        # Special handling for token usage (rate is per 1000 tokens)
        if usage_type in ["input_tokens", "output_tokens"]:
            cost_cents = (quantity * rate_cents_per_unit) // 1000
        else:
            cost_cents = quantity * rate_cents_per_unit

        return UsageCost(
            usage_type=usage_type,
            quantity=quantity,
            cost_cents=cost_cents,
            rate_cents_per_unit=rate_cents_per_unit,
        )

    async def _report_usage_to_provider(self, org_id: str, cost_cents: int):
        """Report usage to payment provider for billing"""
        try:
            # Get subscription for the org
            subscription = await self.billing_service.get_subscription_for_org(org_id)
            if not subscription or not getattr(subscription, "metadata_json", None):
                logger.debug(f"No active subscription found for org {org_id}")
                return

            # Get metered item ID from subscription metadata
            metered_item_id = (subscription.metadata_json or {}).get("metered_item_id")
            if not metered_item_id:
                logger.debug(f"No metered item ID found for org {org_id}")
                return

            # Report usage to payment provider
            # Convert cents to usage units (e.g., dollars)
            usage_quantity = cost_cents  # Report in cents

            success = await self.billing_service.record_usage(org_id, usage_quantity)
            if success:
                logger.info(
                    f"Reported usage to payment provider: {usage_quantity} cents for org {org_id}"
                )
            else:
                logger.warning(
                    f"Failed to report usage to payment provider for org {org_id}"
                )

        except PaymentProviderError as e:
            logger.error(
                f"Payment provider error reporting usage for org {org_id}: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error reporting usage for org {org_id}: {e}")

    def update_pricing_rates(self, rates: Dict[str, int]):
        """Update pricing rates (for admin use)"""
        self.DEFAULT_RATES.update(rates)
        logger.info(f"Updated pricing rates: {rates}")

    def get_pricing_rates(self) -> Dict[str, int]:
        """Get current pricing rates"""
        return self.DEFAULT_RATES.copy()
