from fastapi import APIRouter, HTTPException, Depends, Request, Query
import time
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional
import asyncio
import json
import uuid
from app.api.deps import require_team
from app.db.session import get_db
from app.db import models
from app.streams import queue_for_agent, queue_for_run
from app.observability.metrics import increment_agent_invocations, record_agent_invocation_duration
from app.observability.logging import log_agent_invocation, get_structured_logger, set_request_context

logger = get_structured_logger("agents_invoke")

router = APIRouter()


@router.post("/agents/{agent_id}/invoke")
async def invoke_agent(
    agent_id: str,
    payload: dict,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    org_id = auth.get("org_id")
    capability = payload.get("capability", "unknown")

    # Set observability context (request_id should be set by middleware)
    # set_request_context(getattr(request.state, "request_id", ""), org_id, agent_id)

    run_id = str(uuid.uuid4())
    run = models.Run(
        id=run_id,
        agent_id=agent_id,
        org_id=org_id,
        invoked_by=auth.get("user_id"),
        status="running",
        input=payload,
    )
    db.add(run)
    db.commit()

    agent_q = queue_for_agent(agent_id)
    run_q = queue_for_run(run_id)

    log1 = models.Log(run_id=run_id, level="info", message="started")
    db.add(log1)
    msg1 = json.dumps(
        {"type": "log", "level": "info", "message": "started", "run_id": run_id}
    )
    await agent_q.put(msg1)
    await run_q.put(msg1)
    db.commit()
    await asyncio.sleep(0.05)

    log2 = models.Log(run_id=run_id, level="info", message="doing-work")
    db.add(log2)
    msg2 = json.dumps(
        {"type": "log", "level": "info", "message": "doing-work", "run_id": run_id}
    )
    await agent_q.put(msg2)
    await run_q.put(msg2)
    db.commit()
    await asyncio.sleep(0.05)

    result = {"echo": payload}
    run.status = "succeeded"
    run.output = result
    db.commit()

    complete_msg = json.dumps({"type": "complete", "run_id": run_id, "output": result})
    db.add(models.Log(run_id=run_id, level="info", message=complete_msg))
    db.commit()
    await agent_q.put(complete_msg)
    await run_q.put(complete_msg)

    # Record observability metrics
    duration_ms = (time.time() - start_time) * 1000
    increment_agent_invocations(agent_id, org_id, capability, "succeeded")
    record_agent_invocation_duration(agent_id, org_id, duration_ms)

    # Structured logging
    log_agent_invocation(logger, agent_id, capability, "succeeded", duration_ms, run_id=run_id)

    return {
        "agent_id": agent_id,
        "status": run.status,
        "run_id": run_id,
        "result": result,
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
    try:
        if token:
            from app.security import stack_auth

            profile = stack_auth.verify_stack_access_token(token)
            org_id = (
                team
                or profile.get("selectedTeamId")
                or profile.get("org_id")
                or profile.get("id")
            )
            from app.db.session import set_rls_for_session

            set_rls_for_session(db, org_id)
    except Exception:

        async def err():
            yield 'data: {"type": "error", "message": "auth failed"}\n\n'

        return StreamingResponse(err(), media_type="text/event-stream")

    q = queue_for_agent(agent_id)

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue
            yield f"data: {msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/runs/{run_id}/stream")
async def stream_run_logs(
    run_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        if token:
            from app.security import stack_auth

            profile = stack_auth.verify_stack_access_token(token)
            org_id = (
                team
                or profile.get("selectedTeamId")
                or profile.get("org_id")
                or profile.get("id")
            )
            from app.db.session import set_rls_for_session

            set_rls_for_session(db, org_id)
    except Exception:

        async def err():
            yield 'data: {"type": "error", "message": "auth failed"}\n\n'

        return StreamingResponse(err(), media_type="text/event-stream")

    q = queue_for_run(run_id)

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue
            # Emit the message
            yield f"data: {msg}\n\n"
            # If this is a completion event, close the stream to avoid client hangs
            try:
                obj = json.loads(msg)
                if obj.get("type") == "complete":
                    break
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

