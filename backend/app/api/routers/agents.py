from fastapi import APIRouter, HTTPException, Depends
from app.api.deps import require_auth, require_team
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.db import models
from typing import Any, Dict
import uuid

router = APIRouter()

@router.post("/agents")
async def create_agent(payload: Dict[str, Any], auth=Depends(require_team), db: Session = Depends(get_db)):
    brief = payload.get("brief")
    if not brief:
        raise HTTPException(status_code=400, detail="brief is required")
    org_id = auth.get("org_id")
    user_id = auth.get("user_id")

    # Persist a simple agent row
    agent_id = str(uuid.uuid4())
    agent = models.Agent(id=agent_id, org_id=org_id, created_by=user_id, display_name=brief[:240])
    db.add(agent)
    db.commit()

    return {
        "agent_id": agent_id,
        "org_id": org_id,
        "created_by": user_id,
        "endpoints": {"rest": f"/v1/agents/{agent_id}"},
        "capabilities": [],
    }

@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, auth=Depends(require_auth), db: Session = Depends(get_db)):
    # Enforce that the agent belongs to caller's org
    row = db.query(models.Agent).filter(models.Agent.id == agent_id, models.Agent.org_id == auth.get("org_id")).first()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": row.id,
        "display_name": row.display_name,
        "org_id": row.org_id,
        "created_by": row.created_by,
    }

@router.post("/agents/{agent_id}/invoke")
async def invoke_agent(agent_id: str, payload: dict, auth=Depends(require_team)):
    # TODO: enqueue/run and stream logs
    return {"agent_id": agent_id, "status": "queued", "result": {}}

@router.get("/agents/{agent_id}/instructions")
async def get_instructions(agent_id: str, auth=Depends(require_auth)):
    # TODO: build real instructions
    return {
        "n8n": {"method": "POST", "url": f"/v1/agents/{agent_id}/invoke"},
        "make": {"method": "POST", "url": f"/v1/agents/{agent_id}/invoke"},
        "langchain": {"python": "# example code"},
        "openai": {"tool": "invoke"},
        "claude": {"tool": "invoke"},
        "mcp": {"endpoint": f"wss://TODO/mcp/{agent_id}"},
    }

@router.get("/.well-known/a2a/{agent_id}.json")
async def a2a_descriptor(agent_id: str):
    # TODO: real signed descriptor
    return {
        "id": agent_id,
        "capabilities": [],
        "signature": "TODO",
    }

