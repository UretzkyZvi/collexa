from typing import Callable, Awaitable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
import json
import re
from app.observability.logging import get_structured_logger
from app.security.opa import get_opa_engine

logger = get_structured_logger(__name__)


class PolicyEnforcementMiddleware(BaseHTTPMiddleware):
    """
    OPA Policy enforcement middleware for agent invocations.

    Intercepts POST /v1/agents/{agent_id}/invoke requests and evaluates
    OPA policies before allowing the request to proceed.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ):
        # Only enforce policies on agent invoke endpoints
        if not (
            request.method == "POST" and self._is_agent_invoke_path(request.url.path)
        ):
            return await call_next(request)

        # Skip if no auth context (auth middleware should have handled this)
        auth = getattr(request.state, "auth", None)
        if not auth:
            return await call_next(request)

        # Extract agent_id from path
        agent_id = self._extract_agent_id(request.url.path)
        if not agent_id:
            return await call_next(request)

        # Extract capability from request body
        capability = await self._extract_capability(request)
        if not capability:
            # If we can't extract capability, let the request proceed
            # (it will likely fail validation downstream)
            return await call_next(request)

        # Evaluate policy
        user_id = auth.get("user_id")
        org_id = auth.get("org_id")

        if not user_id or not org_id:
            return JSONResponse(
                {"detail": "Missing user or organization context"}, status_code=403
            )

        opa_engine = get_opa_engine()

        try:
            allowed = await opa_engine.can_invoke_capability(
                user_id=user_id,
                org_id=org_id,
                agent_id=agent_id,
                capability=capability,
                context={"method": request.method, "path": request.url.path},
            )

            if not allowed:
                logger.warning(
                    "Policy denied agent invocation",
                    extra={
                        "user_id": user_id,
                        "org_id": org_id,
                        "agent_id": agent_id,
                        "capability": capability,
                        "event_type": "policy_denial",
                    },
                )
                return JSONResponse(
                    {"detail": "Policy denied access to capability"}, status_code=403
                )

            logger.info(
                "Policy allowed agent invocation",
                extra={
                    "user_id": user_id,
                    "org_id": org_id,
                    "agent_id": agent_id,
                    "capability": capability,
                    "event_type": "policy_allow",
                },
            )

        except Exception as e:
            logger.error(
                "Policy evaluation failed",
                extra={
                    "user_id": user_id,
                    "org_id": org_id,
                    "agent_id": agent_id,
                    "capability": capability,
                    "error": str(e),
                    "event_type": "policy_error",
                },
            )
            # Fail closed - deny access if policy evaluation fails
            return JSONResponse({"detail": "Policy evaluation failed"}, status_code=503)

        return await call_next(request)

    def _is_agent_invoke_path(self, path: str) -> bool:
        """Check if path matches agent invoke pattern."""
        return bool(re.match(r"^/v1/agents/[^/]+/invoke$", path))

    def _extract_agent_id(self, path: str) -> str:
        """Extract agent_id from path like /v1/agents/{agent_id}/invoke."""
        match = re.match(r"^/v1/agents/([^/]+)/invoke$", path)
        return match.group(1) if match else ""

    async def _extract_capability(self, request: Request) -> str:
        """Extract capability from request body."""
        try:
            # Read body and restore it for downstream handlers
            body = await request.body()

            # Parse JSON to extract capability
            if body:
                data = json.loads(body)
                capability = data.get("capability", "")

                # Restore body for downstream consumption
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
                return capability

        except Exception:
            pass

        return ""
