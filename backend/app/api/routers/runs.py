from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import require_auth
from app.db.session import get_db
from app.db import models

router = APIRouter()


@router.get("/runs")
async def list_runs(
    agent_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    auth=Depends(require_auth),
    db: Session = Depends(get_db),
):
    q = db.query(models.Run).filter(models.Run.org_id == auth.get("org_id"))
    if agent_id:
        q = q.filter(models.Run.agent_id == agent_id)
    if status:
        q = q.filter(models.Run.status == status)
    rows = q.order_by(models.Run.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/runs/{run_id}/logs")
async def get_run_logs(
    run_id: str, auth=Depends(require_auth), db: Session = Depends(get_db)
):
    # Ensure run belongs to org
    run = (
        db.query(models.Run)
        .filter(models.Run.id == run_id, models.Run.org_id == auth.get("org_id"))
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    rows = (
        db.query(models.Log)
        .filter(models.Log.run_id == run_id)
        .order_by(models.Log.ts.asc())
        .limit(1000)
        .all()
    )
    return [
        {
            "id": row.id,
            "level": row.level,
            "message": row.message,
            "ts": row.ts.isoformat() if row.ts else None,
        }
        for row in rows
    ]
