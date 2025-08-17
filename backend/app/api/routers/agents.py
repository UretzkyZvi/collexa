from fastapi import APIRouter, HTTPException, Depends, Request, Query
from starlette.responses import StreamingResponse
from app.api.deps import require_auth, require_team
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.db import models
from typing import Any, Dict, Optional
import asyncio
import json
import uuid

# In-memory log queues per agent for SSE (PoC only)
_log_queues: dict[str, asyncio.Queue[str]] = {}

def _queue_for_agent(agent_id: str) -> asyncio.Queue[str]:
    if agent_id not in _log_queues:
        _log_queues[agent_id] = asyncio.Queue(maxsize=1000)
    return _log_queues[agent_id]

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
async def invoke_agent(agent_id: str, payload: dict, auth=Depends(require_team), db: Session = Depends(get_db)):
    # Create a Run row, emit a few mock log lines, finalize with a result
    run_id = str(uuid.uuid4())
    run = models.Run(id=run_id, agent_id=agent_id, org_id=auth.get("org_id"), invoked_by=auth.get("user_id"), status="running", input=payload)
    db.add(run)
    db.commit()

    q = _queue_for_agent(agent_id)
    await q.put(json.dumps({"type": "log", "level": "info", "message": "started", "run_id": run_id}))
    await asyncio.sleep(0.05)
    await q.put(json.dumps({"type": "log", "level": "info", "message": "doing-work", "run_id": run_id}))
    await asyncio.sleep(0.05)

    # finalize
    result = {"echo": payload}
    run.status = "succeeded"
    run.output = result
    db.commit()

    await q.put(json.dumps({"type": "complete", "run_id": run_id, "output": result}))

    return {"agent_id": agent_id, "status": run.status, "run_id": run_id, "result": result}

@router.get("/agents/{agent_id}/instructions")
async def get_instructions(agent_id: str, auth=Depends(require_auth), db: Session = Depends(get_db)):
    """Return ready-to-copy Instructions Pack snippets for an agent.
    Enforces org scoping by ensuring the agent exists in caller's org.
    Snippets use placeholders <host> and <agent-id> that the UI renders.
    """
    row = (
        db.query(models.Agent)
        .filter(models.Agent.id == agent_id, models.Agent.org_id == auth.get("org_id"))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    invoke_url = "https://api.<host>/v1/agents/<agent-id>/invoke"
    a2a_url = "https://<host>/.well-known/a2a/<agent-id>.json"
    mcp_ws = "wss://<host>/mcp/<agent-id>"

    langchain_py = (
        "import requests\n\n"
        "def invoke(capability, payload, host=\"api.<host>\", agent_id=\"<agent-id>\", api_key=\"YOUR_KEY\"):\n"
        "    url = f'https://{host}/v1/agents/{agent_id}/invoke'\n"
        "    r = requests.post(url, headers={\"Authorization\": f\"Bearer {api_key}\"}, json={\"capability\": capability, \"input\": payload}, timeout=60)\n"
        "    r.raise_for_status()\n"
        "    return r.json()\n"
    )

    openai_tool_py = (
        "# Example tool function for OpenAI/Claude that POSTs to /invoke\n"
        "import requests\n\n"
        "def tool_invoke(capability: str, input_json: dict, host=\"api.<host>\", agent_id=\"<agent-id>\", api_key=\"YOUR_KEY\"):\n"
        "    url = f'https://{host}/v1/agents/{agent_id}/invoke'\n"
        "    res = requests.post(url, headers={\"Authorization\": f\"Bearer {api_key}\", \"Content-Type\": \"application/json\"}, json={\"capability\": capability, \"input\": input_json})\n"
        "    res.raise_for_status()\n"
        "    return res.json()\n"
    )

    n8n_text = (
        "Method: POST\n"
        f"URL: {invoke_url}\n"
        "Headers: Authorization: Bearer YOUR_KEY; Content-Type: application/json\n"
        "Body:\n"
        "{\n  \"capability\": \"wireframe.create\",\n  \"input\": { \"screen\": \"onboarding\" }\n}\n"
    )

    make_text = n8n_text  # identical config via HTTP module

    return {
        "agent_id": agent_id,
        "links": {"invoke": invoke_url, "a2a": a2a_url, "mcp": mcp_ws},
        "instructions": [
            {"id": "n8n", "label": "n8n (HTTP Request)", "language": "text", "code": n8n_text},
            {"id": "make", "label": "Make.com (HTTP)", "language": "text", "code": make_text},
            {"id": "langchain_python", "label": "LangChain (Python)", "language": "python", "code": langchain_py},
            {"id": "openai_tool_python", "label": "OpenAI/Claude Tool (Python)", "language": "python", "code": openai_tool_py},
            {"id": "mcp", "label": "MCP Endpoint", "language": "text", "code": mcp_ws},
            {"id": "a2a", "label": "A2A Descriptor", "language": "text", "code": a2a_url},
        ],
    }

@router.get("/agents/{agent_id}/logs")
async def stream_logs(
    agent_id: str,
    request: Request,
    since: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """SSE log stream.
    Accepts token/team as query params for EventSource (cannot set headers).
    Falls back to CORS-protected origin and anonymous if not provided (PoC only).
    """
    # Minimal auth: if token provided, verify and set RLS
    try:
        if token:
            from app.security import stack_auth
            profile = stack_auth.verify_stack_access_token(token)
            org_id = team or profile.get("selectedTeamId") or profile.get("org_id") or profile.get("id")
            from app.db.session import set_rls_for_session
            set_rls_for_session(db, org_id)
    except Exception:
        # On failure, terminate stream
        async def err():
            yield "data: {\"type\": \"error\", \"message\": \"auth failed\"}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    q = _queue_for_agent(agent_id)

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                # Keep-alive comment
                yield ": keep-alive\n\n"
                continue
            yield f"data: {msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/.well-known/a2a/{agent_id}.json")
async def a2a_descriptor(agent_id: str):
    # TODO: real signed descriptor
    return {
        "id": agent_id,
        "capabilities": [],
        "signature": "TODO",
    }

