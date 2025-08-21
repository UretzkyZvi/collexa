from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import json
import hmac
import hashlib
from app.api.deps import require_auth
from app.db.session import get_db
from app.db import models

router = APIRouter()


@router.get("/agents/{agent_id}/instructions")
async def get_instructions(
    agent_id: str, auth=Depends(require_auth), db: Session = Depends(get_db)
):
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
        'def invoke(capability, payload, host="api.<host>", agent_id="<agent-id>", api_key="YOUR_KEY"):\n'
        "    url = f'https://{host}/v1/agents/{agent_id}/invoke'\n"
        '    r = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json={"capability": capability, "input": payload}, timeout=60)\n'
        "    r.raise_for_status()\n"
        "    return r.json()\n"
    )

    openai_tool_py = (
        "# Example tool function for OpenAI/Claude that POSTs to /invoke\n"
        "import requests\n\n"
        'def tool_invoke(capability: str, input_json: dict, host="api.<host>", agent_id="<agent-id>", api_key="YOUR_KEY"):\n'
        "    url = f'https://{host}/v1/agents/{agent_id}/invoke'\n"
        '    res = requests.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json={"capability": capability, "input": input_json})\n'
        "    res.raise_for_status()\n"
        "    return res.json()\n"
    )

    n8n_text = (
        "Method: POST\n"
        f"URL: {invoke_url}\n"
        "Headers: Authorization: Bearer YOUR_KEY; Content-Type: application/json\n"
        "Body:\n"
        '{\n  "capability": "wireframe.create",\n  "input": { "screen": "onboarding" }\n}\n'
    )

    make_text = n8n_text

    return {
        "agent_id": agent_id,
        "links": {"invoke": invoke_url, "a2a": a2a_url, "mcp": mcp_ws},
        "instructions": [
            {
                "id": "n8n",
                "label": "n8n (HTTP Request)",
                "language": "text",
                "code": n8n_text,
            },
            {
                "id": "make",
                "label": "Make.com (HTTP)",
                "language": "text",
                "code": make_text,
            },
            {
                "id": "langchain_python",
                "label": "LangChain (Python)",
                "language": "python",
                "code": langchain_py,
            },
            {
                "id": "openai_tool_python",
                "label": "OpenAI/Claude Tool (Python)",
                "language": "python",
                "code": openai_tool_py,
            },
            {"id": "mcp", "label": "MCP Endpoint", "language": "text", "code": mcp_ws},
            {
                "id": "a2a",
                "label": "A2A Descriptor",
                "language": "text",
                "code": a2a_url,
            },
        ],
    }


@router.get("/.well-known/a2a/{agent_id}.json")
async def a2a_descriptor(agent_id: str):
    secret = os.getenv("APP_SIGNING_SECRET", "dev-secret")
    payload = {
        "id": agent_id,
        "issuer": "collexa",
        "endpoints": {
            "invoke": f"/v1/agents/{agent_id}/invoke",
            "logs": f"/v1/agents/{agent_id}/logs",
            "runs": "/v1/runs",
        },
        "capabilities": ["invoke", "stream_logs", "list_runs"],
    }
    body = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(
        secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return {**payload, "alg": "HS256", "signature": sig}
