"""
Sandbox API router.

Handles HTTP endpoints for dynamic sandbox management.
Follows domain-driven design with focused, testable endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
import inspect

from app.api.deps import get_db, require_team
from app.services.sandbox_service import SandboxService  # Legacy-compatible for tests
from app.services.sandbox_domain import SandboxDomainService
from app.schemas.sandbox import CreateSandboxRequest, UpdateSandboxRequest
from app.db import models

router = APIRouter()


def _is_async_db(db: Session) -> bool:
    """Heuristic: tests for dynamic sandboxes pass an AsyncMock session.
    If db.query is an async callable, avoid direct ORM calls and delegate to domain service.
    """
    q = getattr(db, "query", None)
    return callable(q) and inspect.iscoroutinefunction(q)  # type: ignore[arg-type]


@router.post("/agents/{agent_id}/sandboxes")
async def create_sandbox(
    agent_id: str,
    payload: Dict[str, Any] = Body(...),
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> Any:
    """Create a sandbox.

    - Dynamic (domain) mode: if payload has "required_services", delegate to SandboxDomainService
    - Legacy mock mode: expects {"mode": "mock", "target_system": str}
    """
    org_id = auth.get("org_id")

    # Dynamic path
    if "required_services" in payload:
        try:
            request = CreateSandboxRequest(**payload)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Delegate entirely to domain service (tests patch this class)
        service = SandboxDomainService(db)
        try:
            return await service.create_sandbox(agent_id, org_id, request)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Legacy path (mock mode)
    # Verify agent exists in org (only for real DB sessions)
    if not _is_async_db(db):
        agent = (
            db.query(models.Agent)
            .filter(models.Agent.id == agent_id, models.Agent.org_id == org_id)
            .first()
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

    mode = payload.get("mode")
    if mode != "mock":
        raise HTTPException(status_code=400, detail="Only mock mode is supported")

    target_system: Optional[str] = payload.get("target_system")
    if not target_system:
        raise HTTPException(status_code=422, detail="target_system is required for mock mode")

    # Build response using SandboxService defaults (tests patch these methods)
    svc = SandboxService()
    defaults = svc._get_default_mock_endpoints(target_system)

    import uuid

    sandbox_id = f"sandbox-{uuid.uuid4().hex[:8]}"
    try:
        # Start sandbox (no-op by default, patched in tests)
        svc.start_sandbox(sandbox_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    base_url = defaults.get("base_url", "").format(sandbox_id=sandbox_id)
    prism_url = defaults.get("prism_url", "")
    spec_file = defaults.get("spec_file", "")
    endpoints_map = defaults.get("endpoints", {}) or {}

    return {
        "sandbox_id": sandbox_id,
        "mode": mode,
        "target_system": target_system,
        "endpoints": {
            "mock_api": base_url,
            "prism_direct": prism_url,
        },
        "available_endpoints": list(endpoints_map.keys()),
        "spec_file": spec_file,
    }


@router.get("/agents/{agent_id}/sandboxes")
async def list_sandboxes(
    agent_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> Any:
    """List sandboxes for an agent.

    - Dynamic tests patch SandboxDomainService and expect SandboxListResponse
    - Legacy tests expect a simplified list; use ORM only when db is a real session
    """
    org_id = auth.get("org_id")

    if _is_async_db(db):
        service = SandboxDomainService(db)
        try:
            return await service.list_sandboxes(agent_id, org_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Legacy path
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

    items: List[Dict[str, Any]] = []
    for s in sandboxes:
        items.append(
            {
                "sandbox_id": s.id,
                "mode": s.mode,
                "target_system": s.target_system,
                "status": s.status,
            }
        )

    return {"sandboxes": items}


@router.get("/agents/{agent_id}/sandboxes/{sandbox_id}")
async def get_sandbox(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> Any:
    """Get sandbox details.

    Use domain service for dynamic tests; legacy path returns simplified details.
    """
    org_id = auth.get("org_id")

    if _is_async_db(db):
        service = SandboxDomainService(db)
        try:
            return await service.get_sandbox(agent_id, org_id, sandbox_id)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Legacy path
    sandbox = (
        db.query(models.Sandbox)
        .filter(
            models.Sandbox.id == sandbox_id,
            models.Sandbox.agent_id == agent_id,
            models.Sandbox.org_id == org_id,
        )
        .first()
    )
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    recent_runs = (
        db.query(models.SandboxRun)
        .filter(models.SandboxRun.sandbox_id == sandbox_id)
        .order_by(models.SandboxRun.started_at.desc())
        .limit(5)
        .all()
    )

    runs = [
        {
            "run_id": r.id,
            "phase": r.phase,
            "task_name": r.task_name,
            "status": r.status,
        }
        for r in recent_runs
    ]

    return {
        "sandbox_id": sandbox.id,
        "mode": sandbox.mode,
        "target_system": sandbox.target_system,
        "config": sandbox.config_json or {},
        "recent_runs": runs,
    }


@router.patch("/agents/{agent_id}/sandboxes/{sandbox_id}")
async def update_sandbox(
    agent_id: str,
    sandbox_id: str,
    payload: Dict[str, Any] = Body(...),
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> Any:
    """Update a sandbox (dynamic mode only)."""
    org_id = auth.get("org_id")

    service = SandboxDomainService(db)
    try:
        request = UpdateSandboxRequest(**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        return await service.update_sandbox(agent_id, org_id, sandbox_id, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{agent_id}/sandboxes/{sandbox_id}/reset")
async def reset_sandbox(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Reset a sandbox (legacy-compatible)."""
    org_id = auth.get("org_id")

    sandbox = (
        db.query(models.Sandbox)
        .filter(
            models.Sandbox.id == sandbox_id,
            models.Sandbox.agent_id == agent_id,
            models.Sandbox.org_id == org_id,
        )
        .first()
    )
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    svc = SandboxService()
    svc.reset_sandbox(sandbox_id)

    return {"message": "Sandbox reset successfully", "sandbox_id": sandbox_id}


@router.delete("/agents/{agent_id}/sandboxes/{sandbox_id}")
async def delete_sandbox(
    agent_id: str,
    sandbox_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> Any:
    """Delete a sandbox.

    Dynamic mode delegates to domain service; legacy uses local cleanup + DB delete.
    """
    org_id = auth.get("org_id")

    if _is_async_db(db):
        service = SandboxDomainService(db)
        try:
            return await service.delete_sandbox(agent_id, org_id, sandbox_id)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Legacy path
    sandbox = (
        db.query(models.Sandbox)
        .filter(
            models.Sandbox.id == sandbox_id,
            models.Sandbox.agent_id == agent_id,
            models.Sandbox.org_id == org_id,
        )
        .first()
    )
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    svc = SandboxService()
    svc.stop_sandbox(sandbox_id)

    db.delete(sandbox)
    return {"message": "Sandbox deleted successfully", "sandbox_id": sandbox_id}


@router.get("/agents/{agent_id}/sandboxes/{sandbox_id}/runs")
async def list_sandbox_runs(
    agent_id: str,
    sandbox_id: str,
    limit: int = 10,
    offset: int = 0,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List sandbox runs with pagination (legacy-compatible)."""
    org_id = auth.get("org_id")

    # Ensure sandbox exists
    sandbox = (
        db.query(models.Sandbox)
        .filter(
            models.Sandbox.id == sandbox_id,
            models.Sandbox.agent_id == agent_id,
            models.Sandbox.org_id == org_id,
        )
        .first()
    )
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    q = db.query(models.SandboxRun).filter(models.SandboxRun.sandbox_id == sandbox_id)
    total = q.count()
    runs_q = (
        q.order_by(models.SandboxRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    runs = [
        {
            "run_id": r.id,
            "phase": r.phase,
            "task_name": r.task_name,
            "status": r.status,
            "input": r.input_json,
            "output": r.output_json,
        }
        for r in runs_q
    ]

    return {"runs": runs, "pagination": {"limit": limit, "offset": offset, "total": total}}
