from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Any, Dict
from app.api.deps import require_auth, require_team
from app.db.session import get_db
from app.db import models
import uuid

router = APIRouter()


@router.post("/agents")
async def create_agent(
    payload: Dict[str, Any], auth=Depends(require_team), db: Session = Depends(get_db)
):
    brief = payload.get("brief")
    if not brief:
        raise HTTPException(status_code=400, detail="brief is required")
    org_id = auth.get("org_id")
    user_id = auth.get("user_id")

    agent_id = str(uuid.uuid4())
    agent = models.Agent(
        id=agent_id, org_id=org_id, created_by=user_id, display_name=brief[:240]
    )
    db.add(agent)
    db.commit()

    return {
        "agent_id": agent_id,
        "org_id": org_id,
        "created_by": user_id,
        "endpoints": {"rest": f"/v1/agents/{agent_id}"},
        "capabilities": [],
    }


@router.get("/agents")
async def list_agents(auth=Depends(require_auth), db: Session = Depends(get_db)):
    rows = (
        db.query(models.Agent)
        .filter(models.Agent.org_id == auth.get("org_id"))
        .order_by(models.Agent.created_at.desc())
        .limit(100)
        .all()
    )
    return [{"id": r.id, "display_name": r.display_name} for r in rows]


@router.get("/debug/me")
async def debug_me(auth=Depends(require_auth)):
    return auth


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str, auth=Depends(require_auth), db: Session = Depends(get_db)
):
    row = (
        db.query(models.Agent)
        .filter(models.Agent.id == agent_id, models.Agent.org_id == auth.get("org_id"))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": row.id,
        "display_name": row.display_name,
        "org_id": row.org_id,
        "created_by": row.created_by,
    }

