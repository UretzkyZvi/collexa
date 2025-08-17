from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Any, Dict
from datetime import datetime
import hashlib
import secrets
from app.api.deps import require_team
from app.db.session import get_db
from app.db import models

router = APIRouter()


@router.post("/agents/{agent_id}/keys")
async def issue_agent_key(
    agent_id: str,
    payload: Dict[str, Any] | None = None,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
):
    row = (
        db.query(models.Agent)
        .filter(models.Agent.id == agent_id, models.Agent.org_id == auth.get("org_id"))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    name = (payload or {}).get("name") if payload else None

    key_id = secrets.token_hex(12)
    clear = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(clear.encode("utf-8")).hexdigest()

    db.add(
        models.AgentKey(
            id=key_id,
            org_id=auth.get("org_id"),
            agent_id=agent_id,
            name=name,
            key_hash=key_hash,
            created_by=auth.get("user_id"),
        )
    )
    db.commit()

    return {"key_id": key_id, "api_key": clear}


@router.delete("/agents/{agent_id}/keys/{key_id}")
async def revoke_agent_key(
    agent_id: str, key_id: str, auth=Depends(require_team), db: Session = Depends(get_db)
):
    row = (
        db.query(models.AgentKey)
        .filter(
            models.AgentKey.id == key_id,
            models.AgentKey.agent_id == agent_id,
            models.AgentKey.org_id == auth.get("org_id"),
            models.AgentKey.revoked_at.is_(None),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")
    row.revoked_at = datetime.utcnow()
    db.commit()
    return {"ok": True}

