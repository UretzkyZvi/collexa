from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import require_auth
from app.db.session import get_db
from app.db import models

router = APIRouter()


@router.get("/audit/logs")
async def list_audit_logs(
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    agent_id: Optional[str] = Query(None),
    endpoint: Optional[str] = Query(None),
    auth=Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List audit logs for the current org, with optional filtering."""
    query = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.org_id == auth.get("org_id"))
        .order_by(models.AuditLog.created_at.desc())
    )
    
    if agent_id:
        query = query.filter(models.AuditLog.agent_id == agent_id)
    
    if endpoint:
        query = query.filter(models.AuditLog.endpoint.ilike(f"%{endpoint}%"))
    
    rows = query.offset(offset).limit(limit).all()
    
    return {
        "logs": [
            {
                "id": row.id,
                "actor_id": row.actor_id,
                "endpoint": row.endpoint,
                "agent_id": row.agent_id,
                "capability": row.capability,
                "status_code": row.status_code,
                "request_id": row.request_id,
                "ip_address": row.ip_address,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
        "pagination": {"limit": limit, "offset": offset, "count": len(rows)},
    }
