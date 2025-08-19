from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
import json

from app.api.deps import get_db, require_team
from app.db import models
from app.services.sandbox_service import SandboxService

router = APIRouter()


@router.post("/agents/{agent_id}/sandboxes")
async def create_sandbox(
    agent_id: str,
    payload: Dict[str, Any],
    auth=Depends(require_team),
    db: Session = Depends(get_db),
):
    """Create a new sandbox for an agent (mock mode only for N.1)."""
    org_id = auth.get("org_id")
    
    # Verify agent exists and belongs to org
    agent = (
        db.query(models.Agent)
        .filter(models.Agent.id == agent_id, models.Agent.org_id == org_id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Extract sandbox configuration
    mode = payload.get("mode", "mock")
    target_system = payload.get("target_system")
    config = payload.get("config", {})
    
    # For N.1, only support mock mode
    if mode != "mock":
        raise HTTPException(
            status_code=400, 
            detail="Only mock mode is supported in N.1 implementation"
        )
    
    # Create sandbox
    sandbox_id = str(uuid.uuid4())
    sandbox = models.Sandbox(
        id=sandbox_id,
        agent_id=agent_id,
        org_id=org_id,
        mode=mode,
        target_system=target_system,
        config_json=config,
        status="created"
    )
    
    db.add(sandbox)
    db.commit()
    db.refresh(sandbox)
    
    # Initialize sandbox service and start mock server
    sandbox_service = SandboxService(db)
    await sandbox_service.start_sandbox(sandbox_id)
    
    return {
        "sandbox_id": sandbox_id,
        "agent_id": agent_id,
        "mode": mode,
        "target_system": target_system,
        "status": "created",
        "endpoints": {
            "mock_api": f"http://localhost:4010/{sandbox_id}",  # Prism mock server
            "status": f"/v1/agents/{agent_id}/sandboxes/{sandbox_id}",
            "runs": f"/v1/agents/{agent_id}/sandboxes/{sandbox_id}/runs"
        }
    }


@router.get("/agents/{agent_id}/sandboxes")
async def list_sandboxes(
    agent_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
):
    """List all sandboxes for an agent."""
    org_id = auth.get("org_id")
    
    # Verify agent exists and belongs to org
    agent = (
        db.query(models.Agent)
        .filter(models.Agent.id == agent_id, models.Agent.org_id == org_id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    sandboxes = (
        db.query(models.Sandbox)
        .filter(models.Sandbox.agent_id == agent_id, models.Sandbox.org_id == org_id)
        .order_by(models.Sandbox.created_at.desc())
        .all()
    )
    
    return {
        "sandboxes": [
            {
                "sandbox_id": s.id,
                "mode": s.mode,
                "target_system": s.target_system,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sandboxes
        ]
    }


@router.get("/agents/{agent_id}/sandboxes/{sandbox_id}")
async def get_sandbox(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
):
    """Get sandbox details with recent runs."""
    org_id = auth.get("org_id")
    
    sandbox = (
        db.query(models.Sandbox)
        .filter(
            models.Sandbox.id == sandbox_id,
            models.Sandbox.agent_id == agent_id,
            models.Sandbox.org_id == org_id
        )
        .first()
    )
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    # Get recent runs
    recent_runs = (
        db.query(models.SandboxRun)
        .filter(models.SandboxRun.sandbox_id == sandbox_id)
        .order_by(models.SandboxRun.started_at.desc())
        .limit(10)
        .all()
    )
    
    return {
        "sandbox_id": sandbox.id,
        "agent_id": sandbox.agent_id,
        "mode": sandbox.mode,
        "target_system": sandbox.target_system,
        "config": sandbox.config_json,
        "status": sandbox.status,
        "created_at": sandbox.created_at.isoformat(),
        "updated_at": sandbox.updated_at.isoformat(),
        "recent_runs": [
            {
                "run_id": r.id,
                "phase": r.phase,
                "task_name": r.task_name,
                "status": r.status,
                "started_at": r.started_at.isoformat(),
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in recent_runs
        ]
    }


@router.post("/agents/{agent_id}/sandboxes/{sandbox_id}/reset")
async def reset_sandbox(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
):
    """Reset sandbox state while preserving provenance."""
    org_id = auth.get("org_id")
    
    sandbox = (
        db.query(models.Sandbox)
        .filter(
            models.Sandbox.id == sandbox_id,
            models.Sandbox.agent_id == agent_id,
            models.Sandbox.org_id == org_id
        )
        .first()
    )
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    # Reset sandbox via service
    sandbox_service = SandboxService(db)
    await sandbox_service.reset_sandbox(sandbox_id)
    
    return {"message": "Sandbox reset successfully", "sandbox_id": sandbox_id}


@router.delete("/agents/{agent_id}/sandboxes/{sandbox_id}")
async def delete_sandbox(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
):
    """Delete sandbox and all associated data."""
    org_id = auth.get("org_id")
    
    sandbox = (
        db.query(models.Sandbox)
        .filter(
            models.Sandbox.id == sandbox_id,
            models.Sandbox.agent_id == agent_id,
            models.Sandbox.org_id == org_id
        )
        .first()
    )
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    # Stop and cleanup sandbox
    sandbox_service = SandboxService(db)
    await sandbox_service.stop_sandbox(sandbox_id)
    
    # Delete from database (cascades to runs)
    db.delete(sandbox)
    db.commit()
    
    return {"message": "Sandbox deleted successfully", "sandbox_id": sandbox_id}


@router.get("/agents/{agent_id}/sandboxes/{sandbox_id}/runs")
async def list_sandbox_runs(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """List sandbox runs with pagination."""
    org_id = auth.get("org_id")
    
    # Verify sandbox exists and belongs to org
    sandbox = (
        db.query(models.Sandbox)
        .filter(
            models.Sandbox.id == sandbox_id,
            models.Sandbox.agent_id == agent_id,
            models.Sandbox.org_id == org_id
        )
        .first()
    )
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    runs = (
        db.query(models.SandboxRun)
        .filter(models.SandboxRun.sandbox_id == sandbox_id)
        .order_by(models.SandboxRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return {
        "runs": [
            {
                "run_id": r.id,
                "phase": r.phase,
                "task_name": r.task_name,
                "status": r.status,
                "input": r.input_json,
                "output": r.output_json,
                "error": r.error_json,
                "started_at": r.started_at.isoformat(),
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in runs
        ],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": db.query(models.SandboxRun).filter(models.SandboxRun.sandbox_id == sandbox_id).count()
        }
    }
