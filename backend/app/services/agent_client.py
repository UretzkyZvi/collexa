from typing import Any, Dict, Optional
import os
from app.services.http_client import get_http_client

API_BASE = os.getenv("INTERNAL_API_BASE_URL", os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")


async def invoke_agent_http(
    agent_id: str,
    payload: Dict[str, Any],
    *,
    access_token: Optional[str] = None,
    team_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Invoke another agent via HTTP using the shared AsyncClient.

    This enables cross-agent scenarios and reuses pooled connections.
    """
    client = get_http_client()
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if team_id:
        headers["X-Team-Id"] = team_id

    url = f"{API_BASE}/v1/agents/{agent_id}/invoke"
    resp = await client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

