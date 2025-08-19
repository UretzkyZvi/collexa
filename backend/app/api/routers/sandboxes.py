"""
Sandbox API router.

Handles HTTP endpoints for dynamic sandbox management.
Follows domain-driven design with focused, testable endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_team
from app.services.sandbox_domain import SandboxDomainService
from app.schemas.sandbox import (
    CreateSandboxRequest,
    UpdateSandboxRequest,
    SandboxResponse,
    SandboxListResponse,
    DeleteSandboxResponse
)

router = APIRouter()


@router.post("/agents/{agent_id}/sandboxes", response_model=SandboxResponse)
async def create_sandbox(
    agent_id: str,
    request: CreateSandboxRequest,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> SandboxResponse:
    """Create a new dynamic sandbox for an agent."""
    org_id = auth.get("org_id")
    
    try:
        service = SandboxDomainService(db)
        return await service.create_sandbox(agent_id, org_id, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents/{agent_id}/sandboxes/{sandbox_id}", response_model=SandboxResponse)
async def get_sandbox(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> SandboxResponse:
    """Get information about a specific sandbox."""
    org_id = auth.get("org_id")
    
    try:
        service = SandboxDomainService(db)
        return await service.get_sandbox(agent_id, org_id, sandbox_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agents/{agent_id}/sandboxes", response_model=SandboxListResponse)
async def list_sandboxes(
    agent_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> SandboxListResponse:
    """List all sandboxes for an agent."""
    org_id = auth.get("org_id")
    
    try:
        service = SandboxDomainService(db)
        return await service.list_sandboxes(agent_id, org_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/agents/{agent_id}/sandboxes/{sandbox_id}", response_model=SandboxResponse)
async def update_sandbox(
    agent_id: str,
    sandbox_id: str,
    request: UpdateSandboxRequest,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> SandboxResponse:
    """Update a sandbox by adding services or updating configurations."""
    org_id = auth.get("org_id")
    
    try:
        service = SandboxDomainService(db)
        return await service.update_sandbox(agent_id, org_id, sandbox_id, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/agents/{agent_id}/sandboxes/{sandbox_id}", response_model=DeleteSandboxResponse)
async def delete_sandbox(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> DeleteSandboxResponse:
    """Delete a sandbox and cleanup all its resources."""
    org_id = auth.get("org_id")
    
    try:
        service = SandboxDomainService(db)
        return await service.delete_sandbox(agent_id, org_id, sandbox_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
