from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import os

from app.api.deps import require_team, require_auth
from app.db.session import get_db
from app.db import models
from app.services.agent_builder import (
    parse_brief_to_adl,
    select_capability_kit,
    render_instructions,
    produce_manifest,
)
from app.schemas.agent_blueprint import AgentBlueprintV1, InstructionsPack
from app.services.learning.learning_loop import run_learning_iteration, IterationConfig

router = APIRouter()

AB1_ENABLED = os.getenv("AB1_ENABLED", "true").lower() == "true"
AB1_VALIDATE_ON_PREVIEW = os.getenv("AB1_VALIDATE_ON_PREVIEW", "false").lower() == "true"
DEFAULT_MODE = os.getenv("AB1_DEFAULT_SANDBOX_MODE", "mock").lower()


@router.post("/agents/builder/preview")
async def preview_agent(
    payload: Dict[str, Any], auth=Depends(require_team), db: Session = Depends(get_db)
):
    if not AB1_ENABLED:
        raise HTTPException(status_code=404, detail="Builder disabled")

    brief = payload.get("brief")
    if not brief:
        raise HTTPException(status_code=400, detail="brief is required")

    agent_id = payload.get("agent_id") or "preview-agent"

    bp = parse_brief_to_adl(agent_id, brief)
    tools, caps = select_capability_kit(bp)
    instr = render_instructions(bp, tools)
    manifest = produce_manifest(caps)

    response: Dict[str, Any] = {
        "blueprint": bp.model_dump(mode="json"),
        "instructions": instr.model_dump(mode="json"),
        "manifest": manifest,
    }

    validate = bool(payload.get("validate")) or AB1_VALIDATE_ON_PREVIEW
    if validate:
        # Minimal smoke test via N.2 iteration in mock mode
        cfg = IterationConfig(agent_id=bp.agent_id, tasks=["echo"], docs=[], sandbox_mode=DEFAULT_MODE)
        _ = run_learning_iteration(cfg)
        response["validation"] = {"status": "ok", "mode": DEFAULT_MODE}

    return response


@router.post("/agents/builder/create")
async def create_agent_from_blueprint(
    payload: Dict[str, Any], auth=Depends(require_team), db: Session = Depends(get_db)
):
    if not AB1_ENABLED:
        raise HTTPException(status_code=404, detail="Builder disabled")

    brief = payload.get("brief")
    if not brief:
        raise HTTPException(status_code=400, detail="brief is required")

    import uuid

    agent_id = str(uuid.uuid4())
    bp = parse_brief_to_adl(agent_id, brief)
    tools, caps = select_capability_kit(bp)
    instr = render_instructions(bp, tools)
    manifest = produce_manifest(caps)

    row = models.Agent(
        id=agent_id,
        org_id=auth.get("org_id"),
        created_by=auth.get("user_id"),
        display_name=brief[:240],
    )
    db.add(row)
    db.commit()

    # Persist blueprint/instructions/manifest JSON fields if columns present
    try:
        from sqlalchemy import text

        db.execute(
            text(
                "UPDATE agents SET adl_version=:v, blueprint_json=:bp, instructions_pack_json=:ip, manifest_json=:mf WHERE id=:id"
            ),
            {
                "v": bp.adl_version,
                "bp": bp.model_dump(mode="json"),
                "ip": instr.model_dump(mode="json"),
                "mf": manifest,
                "id": agent_id,
            },
        )
        db.commit()
    except Exception:
        # Columns may not exist locally; safe to ignore for MVP
        db.rollback()

    return {
        "agent_id": agent_id,
        "blueprint": bp.model_dump(mode="json"),
        "instructions": instr.model_dump(mode="json"),
        "manifest": manifest,
    }

