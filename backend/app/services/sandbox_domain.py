"""
Domain service for sandbox operations.

This service handles the business logic for sandbox management,
acting as a bridge between the API layer and the orchestrator.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.sandbox import (
    CreateSandboxRequest,
    UpdateSandboxRequest,
    SandboxResponse,
    SandboxServiceResponse,
    SandboxListResponse,
    DeleteSandboxResponse,
)

# Lazy import to avoid importing heavy docker client in environments (like CI) that don't need it at import time.
# Tests patch SandboxDomainService methods; importing orchestrator only
# when methods run prevents ModuleNotFoundError: docker.
orchestrator = None  # type: ignore[assignment]
SandboxRequest = None  # type: ignore[assignment]
ServiceConfig = None  # type: ignore[assignment]


def _ensure_orchestrator_loaded():
    global orchestrator, SandboxRequest, ServiceConfig
    if orchestrator is None:
        from app.services.sandbox_orchestrator import (
            orchestrator as _orch,
            SandboxRequest as _SandboxRequest,
            ServiceConfig as _ServiceConfig,
        )

        orchestrator = _orch
        SandboxRequest = _SandboxRequest
        ServiceConfig = _ServiceConfig


class SandboxDomainService:
    """
    Domain service for sandbox operations.

    Handles business logic, validation, and coordination between
    the API layer and the underlying orchestrator.
    """

    def __init__(self, db: Session):
        self.db = db

    async def create_sandbox(
        self, agent_id: str, org_id: str, request: CreateSandboxRequest
    ) -> SandboxResponse:
        """Create a new dynamic sandbox for an agent."""

        # Verify agent exists and belongs to org
        self._get_agent_or_raise(agent_id, org_id)

        # Convert schema to orchestrator request
        orchestrator_request = self._convert_to_orchestrator_request(request)

        # Create sandbox using orchestrator
        _ensure_orchestrator_loaded()
        try:
            sandbox_info = await orchestrator.create_sandbox(  # type: ignore[union-attr]
                agent_id, orchestrator_request
            )
        except Exception as e:
            raise Exception(f"Failed to create sandbox: {str(e)}")

        # Convert to response schema
        return self._convert_to_response(sandbox_info, request.ttl_minutes)

    async def get_sandbox(
        self, agent_id: str, org_id: str, sandbox_id: str
    ) -> SandboxResponse:
        """Get information about a specific sandbox."""

        # Verify agent exists and belongs to org
        self._get_agent_or_raise(agent_id, org_id)

        # Get sandbox from orchestrator
        _ensure_orchestrator_loaded()
        # type: ignore[union-attr]
        sandbox_info = await orchestrator.get_sandbox(sandbox_id)
        if not sandbox_info or sandbox_info.agent_id != agent_id:
            raise Exception("Sandbox not found")

        # Convert to response schema
        return self._convert_to_response(sandbox_info)

    async def list_sandboxes(self, agent_id: str, org_id: str) -> SandboxListResponse:
        """List all sandboxes for an agent."""

        # Verify agent exists and belongs to org
        self._get_agent_or_raise(agent_id, org_id)

        # Get all active sandboxes and filter by agent
        _ensure_orchestrator_loaded()
        all_sandboxes = orchestrator.get_active_sandboxes()  # type: ignore[union-attr]
        agent_sandboxes = [
            self._convert_to_response(sandbox_info)
            for sandbox_info in all_sandboxes.values()
            if sandbox_info.agent_id == agent_id
        ]

        return SandboxListResponse(
            sandboxes=agent_sandboxes, total=len(agent_sandboxes)
        )

    async def update_sandbox(
        self, agent_id: str, org_id: str, sandbox_id: str, request: UpdateSandboxRequest
    ) -> SandboxResponse:
        """Update an existing sandbox."""

        # Verify agent exists and belongs to org
        self._get_agent_or_raise(agent_id, org_id)

        # Verify sandbox exists and belongs to agent
        sandbox_info = await orchestrator.get_sandbox(sandbox_id)
        if not sandbox_info or sandbox_info.agent_id != agent_id:
            raise Exception("Sandbox not found")

        # Convert update request
        add_services = request.add_services or []
        update_configs = {}

        if request.update_configs:
            for service_type, config_schema in request.update_configs.items():
                update_configs[service_type] = ServiceConfig(
                    service_type=service_type,
                    custom_responses=config_schema.custom_responses,
                    custom_endpoints=config_schema.custom_endpoints,
                    workspace_config=config_schema.workspace_config,
                )

        # Update sandbox using orchestrator
        _ensure_orchestrator_loaded()
        try:
            updated_sandbox = await orchestrator.update_sandbox(  # type: ignore[union-attr]
                sandbox_id, add_services=add_services, update_configs=update_configs
            )
        except Exception as e:
            raise Exception(f"Failed to update sandbox: {str(e)}")

        # Convert to response schema
        return self._convert_to_response(updated_sandbox)

    async def delete_sandbox(
        self, agent_id: str, org_id: str, sandbox_id: str
    ) -> DeleteSandboxResponse:
        """Delete a sandbox and cleanup all its resources."""

        # Verify agent exists and belongs to org
        self._get_agent_or_raise(agent_id, org_id)

        # Verify sandbox exists and belongs to agent
        sandbox_info = await orchestrator.get_sandbox(sandbox_id)
        if not sandbox_info or sandbox_info.agent_id != agent_id:
            raise Exception("Sandbox not found")

        # Delete sandbox using orchestrator
        _ensure_orchestrator_loaded()
        # type: ignore[union-attr]
        success = await orchestrator.delete_sandbox(sandbox_id)
        if not success:
            raise Exception("Failed to delete sandbox")

        return DeleteSandboxResponse(
            message="Sandbox deleted successfully", sandbox_id=sandbox_id
        )

    async def cleanup_expired_sandboxes(self) -> int:
        """Cleanup expired sandboxes and return count of cleaned up sandboxes."""
        before_count = len(orchestrator.get_active_sandboxes())
        await orchestrator.cleanup_expired_sandboxes()
        after_count = len(orchestrator.get_active_sandboxes())
        return before_count - after_count

    def _get_agent_or_raise(self, agent_id: str, org_id: str) -> models.Agent:
        """Get agent or raise exception if not found or doesn't belong to org."""
        agent = (
            self.db.query(models.Agent)
            .filter(models.Agent.id == agent_id, models.Agent.org_id == org_id)
            .first()
        )
        if not agent:
            raise Exception("Agent not found")
        return agent

    def _convert_to_orchestrator_request(self, request: CreateSandboxRequest):
        """Convert API request schema to orchestrator request."""
        _ensure_orchestrator_loaded()
        custom_configs = {}

        for service_type, config_schema in request.custom_configs.items():
            custom_configs[service_type] = ServiceConfig(
                service_type=service_type,
                custom_responses=config_schema.custom_responses,
                custom_endpoints=config_schema.custom_endpoints,
                workspace_config=config_schema.workspace_config,
            )

        return SandboxRequest(
            required_services=request.required_services,
            custom_configs=custom_configs,
            ttl_minutes=request.ttl_minutes,
            resource_limits=request.resource_limits,
        )

    def _convert_to_response(
        self, sandbox_info, ttl_minutes: Optional[int] = None
    ) -> SandboxResponse:
        """Convert orchestrator sandbox info to API response schema."""
        services = {}
        for name, service in sandbox_info.services.items():
            services[name] = SandboxServiceResponse(
                url=service.url, status=service.status, endpoints=service.endpoints
            )

        return SandboxResponse(
            sandbox_id=sandbox_info.sandbox_id,
            agent_id=sandbox_info.agent_id,
            status=sandbox_info.status,
            services=services,
            proxy_url=sandbox_info.proxy_url,
            created_at=sandbox_info.created_at,
            expires_at=sandbox_info.expires_at,
            last_accessed=sandbox_info.last_accessed,
            ttl_minutes=ttl_minutes,
        )
