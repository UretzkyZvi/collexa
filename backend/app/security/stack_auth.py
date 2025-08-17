import os
from typing import Any, Dict
import requests
from fastapi import HTTPException

STACK_API_BASE = os.getenv("STACK_API_BASE", "https://api.stack-auth.com/api/v1")
STACK_PROJECT_ID = os.getenv("STACK_PROJECT_ID", "")
STACK_SECRET_SERVER_KEY = os.getenv("STACK_SECRET_SERVER_KEY", "")


def verify_stack_access_token(access_token: str) -> Dict[str, Any]:
    if not STACK_PROJECT_ID or not STACK_SECRET_SERVER_KEY:
        raise HTTPException(status_code=500, detail="Stack Auth is not configured (missing project/server key)")

    url = f"{STACK_API_BASE}/users/me"
    headers = {
        "x-stack-access-type": "server",
        "x-stack-project-id": STACK_PROJECT_ID,
        "x-stack-secret-server-key": STACK_SECRET_SERVER_KEY,
        "x-stack-access-token": access_token,
    }
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    return r.json()


def verify_team_membership(team_id: str, access_token: str) -> Dict[str, Any]:
    """Verify that the user (by access_token) is a member of the given team.
    Uses Stack's team-member-profiles endpoint. Returns the team member profile if valid.
    """
    url = f"{STACK_API_BASE}/team-member-profiles/{team_id}/me"
    headers = {
        "x-stack-access-token": access_token,
    }
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return r.json()
