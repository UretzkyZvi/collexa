"""
Pydantic schemas for sandbox-related API requests and responses.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ServiceConfigSchema(BaseModel):
    """Configuration for a mock service within a sandbox."""

    service_type: str = Field(
        ..., description="Type of service (figma, slack, github, etc.)"
    )
    custom_responses: Dict[str, Any] = Field(
        default_factory=dict, description="Custom mock responses for endpoints"
    )
    custom_endpoints: List[Dict[str, Any]] = Field(
        default_factory=list, description="Additional custom endpoints"
    )
    workspace_config: Dict[str, Any] = Field(
        default_factory=dict, description="Workspace-specific configuration"
    )


class CreateSandboxRequest(BaseModel):
    """Request to create a new dynamic sandbox."""

    required_services: List[str] = Field(
        ..., description="List of services to include in the sandbox"
    )
    custom_configs: Dict[str, ServiceConfigSchema] = Field(
        default_factory=dict, description="Custom configurations per service"
    )
    ttl_minutes: int = Field(
        default=60, ge=1, le=1440, description="Time-to-live in minutes (1-1440)"
    )
    resource_limits: Dict[str, Any] = Field(
        default_factory=dict, description="Resource limits for the sandbox"
    )


class UpdateSandboxRequest(BaseModel):
    """Request to update an existing sandbox."""

    add_services: Optional[List[str]] = Field(
        None, description="Services to add to the sandbox"
    )
    update_configs: Optional[Dict[str, ServiceConfigSchema]] = Field(
        None, description="Service configurations to update"
    )


class SandboxServiceResponse(BaseModel):
    """Information about a running service within a sandbox."""

    url: str = Field(..., description="Service endpoint URL")
    status: str = Field(
        ..., description="Service status (starting, running, stopping, stopped)"
    )
    endpoints: List[str] = Field(
        default_factory=list, description="Available API endpoints"
    )


class SandboxResponse(BaseModel):
    """Response containing sandbox information."""

    sandbox_id: str = Field(..., description="Unique sandbox identifier")
    agent_id: str = Field(..., description="Agent that owns this sandbox")
    status: str = Field(
        ..., description="Sandbox status (creating, running, stopping, stopped)"
    )
    services: Dict[str, SandboxServiceResponse] = Field(
        default_factory=dict, description="Running services in the sandbox"
    )
    proxy_url: str = Field(..., description="Proxy URL for accessing sandbox services")
    created_at: datetime = Field(..., description="Sandbox creation timestamp")
    expires_at: datetime = Field(..., description="Sandbox expiration timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    ttl_minutes: Optional[int] = Field(None, description="Time-to-live in minutes")


class SandboxListResponse(BaseModel):
    """Response containing list of sandboxes."""

    sandboxes: List[SandboxResponse] = Field(
        default_factory=list, description="List of sandboxes"
    )
    total: int = Field(..., description="Total number of sandboxes")


class DeleteSandboxResponse(BaseModel):
    """Response for sandbox deletion."""

    message: str = Field(..., description="Deletion confirmation message")
    sandbox_id: str = Field(..., description="ID of the deleted sandbox")
