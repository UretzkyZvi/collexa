import httpx
import json
import os
from typing import Dict, Any, Optional
import asyncio


class OPAPolicyEngine:
    def __init__(self, opa_url: str = None):
        self.opa_url = opa_url or os.getenv("OPA_URL", "http://localhost:8181")
        # Reuse shared pooled client for efficiency
        from app.services.http_client import get_http_client

        self.client = get_http_client()
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def evaluate_policy(
        self, policy_path: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate OPA policy with input data.

        Args:
            policy_path: Policy path like "collexa/authz/invoke"
            input_data: Input data for policy evaluation

        Returns:
            Policy evaluation result

        Raises:
            Exception: If OPA evaluation fails
        """
        url = f"{self.opa_url}/v1/data/{policy_path}"

        try:
            response = await self.client.post(
                url,
                json={"input": input_data},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                raise Exception(
                    f"OPA evaluation failed: {response.status_code} {response.text}"
                )

            return response.json()
        except httpx.RequestError as e:
            raise Exception(f"OPA request failed: {e}")

    async def can_invoke_capability(
        self,
        user_id: str,
        org_id: str,
        agent_id: str,
        capability: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if user can invoke a specific capability.

        Args:
            user_id: User identifier
            org_id: Organization identifier
            agent_id: Agent identifier
            capability: Capability name
            context: Additional context for policy evaluation

        Returns:
            True if allowed, False otherwise
        """
        input_data = {
            "user": {"id": user_id},
            "org": {"id": org_id},
            "agent": {"id": agent_id},
            "capability": capability,
            "context": context or {},
        }

        try:
            result = await self.evaluate_policy("collexa/authz/invoke", input_data)
            return result.get("result", {}).get("allow", False)
        except Exception:
            # Fail closed - deny access if policy evaluation fails
            return False

    async def health_check(self) -> bool:
        """Check if OPA is healthy and reachable."""
        try:
            response = await self.client.get(f"{self.opa_url}/health")
            return response.status_code == 200
        except Exception:
            return False


# Global instance for use in middleware
_opa_engine: Optional[OPAPolicyEngine] = None


def get_opa_engine() -> OPAPolicyEngine:
    """Get or create the global OPA engine instance."""
    global _opa_engine
    if _opa_engine is None:
        _opa_engine = OPAPolicyEngine()
    return _opa_engine


async def cleanup_opa_engine():
    """Cleanup the global OPA engine instance."""
    global _opa_engine
    if _opa_engine is not None:
        await _opa_engine.close()
        _opa_engine = None
