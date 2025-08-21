"""
Cost calculation service.

This service handles pricing calculations for different usage types
and provides flexible pricing management.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class UsageType(Enum):
    """Supported usage types"""

    INVOCATION = "invocation"
    INPUT_TOKENS = "input_tokens"
    OUTPUT_TOKENS = "output_tokens"
    STORAGE_MB = "storage_mb"
    LEARNING_HOUR = "learning_hour"


@dataclass
class UsageCost:
    """Usage cost calculation result"""

    usage_type: str
    quantity: int
    cost_cents: int
    rate_cents_per_unit: int
    description: str


@dataclass
class PricingTier:
    """Pricing tier for volume-based pricing"""

    min_quantity: int
    max_quantity: Optional[int]  # None for unlimited
    rate_cents_per_unit: int


class CostCalculationService:
    """Service for calculating usage costs"""

    def __init__(self):
        # Default pricing rates (cents per unit)
        self._base_rates = {
            UsageType.INVOCATION.value: 10,  # 10 cents per invocation
            UsageType.INPUT_TOKENS.value: 1,  # 1 cent per 1000 input tokens
            UsageType.OUTPUT_TOKENS.value: 2,  # 2 cents per 1000 output tokens
            UsageType.STORAGE_MB.value: 5,  # 5 cents per MB per month
            UsageType.LEARNING_HOUR.value: 100,  # $1 per learning hour
        }

        # Tiered pricing (optional, for volume discounts)
        self._pricing_tiers: Dict[str, List[PricingTier]] = {}

        # Custom pricing overrides (org_id -> usage_type -> rate)
        self._custom_pricing: Dict[str, Dict[str, int]] = {}

    def calculate_cost(
        self, usage_type: str, quantity: int, org_id: Optional[str] = None
    ) -> UsageCost:
        """
        Calculate cost for a usage type and quantity.

        Args:
            usage_type: Type of usage (invocation, tokens, etc.)
            quantity: Number of units used
            org_id: Organization ID (for custom pricing)

        Returns:
            UsageCost with calculated cost and details
        """
        # Get the rate for this usage type
        rate_cents_per_unit = self._get_rate(usage_type, quantity, org_id)

        # Calculate cost based on usage type
        if usage_type in [UsageType.INPUT_TOKENS.value, UsageType.OUTPUT_TOKENS.value]:
            # Token usage is priced per 1000 tokens
            cost_cents = (quantity * rate_cents_per_unit) // 1000
        else:
            # Other usage types are priced per unit
            cost_cents = quantity * rate_cents_per_unit

        return UsageCost(
            usage_type=usage_type,
            quantity=quantity,
            cost_cents=cost_cents,
            rate_cents_per_unit=rate_cents_per_unit,
            description=self._get_usage_description(usage_type),
        )

    def calculate_invocation_cost(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        org_id: Optional[str] = None,
    ) -> List[UsageCost]:
        """
        Calculate cost for a complete agent invocation.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            org_id: Organization ID (for custom pricing)

        Returns:
            List of UsageCost for each component
        """
        costs = []

        # Base invocation cost
        costs.append(self.calculate_cost(UsageType.INVOCATION.value, 1, org_id))

        # Token costs (only if non-zero)
        if input_tokens > 0:
            costs.append(
                self.calculate_cost(UsageType.INPUT_TOKENS.value, input_tokens, org_id)
            )

        if output_tokens > 0:
            costs.append(
                self.calculate_cost(
                    UsageType.OUTPUT_TOKENS.value, output_tokens, org_id
                )
            )

        return costs

    def calculate_total_cost(self, usage_costs: List[UsageCost]) -> int:
        """Calculate total cost from a list of usage costs"""
        return sum(cost.cost_cents for cost in usage_costs)

    def estimate_invocation_cost(
        self,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        org_id: Optional[str] = None,
    ) -> int:
        """
        Estimate cost for an invocation (for budget checking).

        Args:
            estimated_input_tokens: Estimated input tokens
            estimated_output_tokens: Estimated output tokens
            org_id: Organization ID (for custom pricing)

        Returns:
            Estimated cost in cents
        """
        costs = self.calculate_invocation_cost(
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
            org_id=org_id,
        )
        return self.calculate_total_cost(costs)

    def set_custom_pricing(
        self, org_id: str, usage_type: str, rate_cents_per_unit: int
    ):
        """
        Set custom pricing for an organization.

        Args:
            org_id: Organization ID
            usage_type: Usage type to set pricing for
            rate_cents_per_unit: Rate in cents per unit
        """
        if org_id not in self._custom_pricing:
            self._custom_pricing[org_id] = {}

        self._custom_pricing[org_id][usage_type] = rate_cents_per_unit
        logger.info(
            f"Set custom pricing for org {org_id}: {usage_type} = {rate_cents_per_unit} cents/unit"
        )

    def remove_custom_pricing(self, org_id: str, usage_type: Optional[str] = None):
        """
        Remove custom pricing for an organization.

        Args:
            org_id: Organization ID
            usage_type: Specific usage type (None to remove all)
        """
        if org_id not in self._custom_pricing:
            return

        if usage_type:
            self._custom_pricing[org_id].pop(usage_type, None)
        else:
            del self._custom_pricing[org_id]

        logger.info(
            f"Removed custom pricing for org {org_id}, usage_type: {usage_type}"
        )

    def set_pricing_tiers(self, usage_type: str, tiers: List[PricingTier]):
        """
        Set tiered pricing for a usage type.

        Args:
            usage_type: Usage type
            tiers: List of pricing tiers (sorted by min_quantity)
        """
        # Sort tiers by min_quantity
        sorted_tiers = sorted(tiers, key=lambda t: t.min_quantity)
        self._pricing_tiers[usage_type] = sorted_tiers
        logger.info(f"Set {len(tiers)} pricing tiers for {usage_type}")

    def get_pricing_rates(self, org_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get current pricing rates for an organization.

        Args:
            org_id: Organization ID (for custom pricing)

        Returns:
            Dictionary of usage_type -> rate_cents_per_unit
        """
        rates = self._base_rates.copy()

        # Apply custom pricing if available
        if org_id and org_id in self._custom_pricing:
            rates.update(self._custom_pricing[org_id])

        return rates

    def get_usage_descriptions(self) -> Dict[str, str]:
        """Get descriptions for all usage types"""
        return {
            usage_type: self._get_usage_description(usage_type)
            for usage_type in self._base_rates.keys()
        }

    def update_base_rates(self, rates: Dict[str, int]):
        """
        Update base pricing rates (admin function).

        Args:
            rates: Dictionary of usage_type -> rate_cents_per_unit
        """
        self._base_rates.update(rates)
        logger.info(f"Updated base pricing rates: {rates}")

    # Private helper methods

    def _get_rate(
        self, usage_type: str, quantity: int, org_id: Optional[str] = None
    ) -> int:
        """Get the rate for a usage type, considering tiers and custom pricing"""
        # Check for custom pricing first
        if org_id and org_id in self._custom_pricing:
            custom_rate = self._custom_pricing[org_id].get(usage_type)
            if custom_rate is not None:
                return custom_rate

        # Check for tiered pricing
        if usage_type in self._pricing_tiers:
            for tier in self._pricing_tiers[usage_type]:
                if quantity >= tier.min_quantity:
                    if tier.max_quantity is None or quantity <= tier.max_quantity:
                        return tier.rate_cents_per_unit

        # Fall back to base rate
        return self._base_rates.get(usage_type, 0)

    def _get_usage_description(self, usage_type: str) -> str:
        """Get human-readable description for usage type"""
        descriptions = {
            UsageType.INVOCATION.value: "Per agent invocation",
            UsageType.INPUT_TOKENS.value: "Per 1000 input tokens",
            UsageType.OUTPUT_TOKENS.value: "Per 1000 output tokens",
            UsageType.STORAGE_MB.value: "Per MB per month",
            UsageType.LEARNING_HOUR.value: "Per learning hour",
        }
        return descriptions.get(usage_type, f"Per {usage_type} unit")


# Global instance for easy access
cost_calculator = CostCalculationService()
