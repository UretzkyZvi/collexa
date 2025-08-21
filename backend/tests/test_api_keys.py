import hashlib
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db, SessionLocal
from app.db import models

client = TestClient(app)


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def test_issue_and_use_api_key(monkeypatch):
    # monkeypatch stack auth to accept user1-token and team org1
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth,
        "verify_stack_access_token",
        lambda t: {"id": "user1", "selectedTeamId": "org1"},
    )
    monkeypatch.setattr(
        stack_auth, "verify_team_membership", lambda team, tok: {"id": team}
    )

    # Create an agent via team auth
    r = client.post(
        "/v1/agents",
        json={"brief": "key test"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]

    # Issue an API key for the agent
    r2 = client.post(
        f"/v1/agents/{agent_id}/keys",
        json={"name": "test"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    assert r2.status_code == 200
    api_key = r2.json()["api_key"]

    # Use X-API-Key to invoke without Authorization
    r3 = client.post(
        f"/v1/agents/{agent_id}/invoke",
        json={"capability": "test", "input": {"x": 1}},
        headers={"X-API-Key": api_key},
    )
    if r3.status_code != 200:
        print(f"Error: {r3.status_code} - {r3.text}")
    assert r3.status_code == 200
    body = r3.json()
    assert body["agent_id"] == agent_id

    # Revoke key
    # Need to find key_id from DB
    db = SessionLocal()
    try:
        key_row = (
            db.query(models.AgentKey)
            .filter(models.AgentKey.key_hash == _hash(api_key))
            .first()
        )
        key_id = key_row.id
    finally:
        db.close()

    r4 = client.delete(
        f"/v1/agents/{agent_id}/keys/{key_id}",
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    assert r4.status_code == 200

    # After revocation, X-API-Key should fail
    r5 = client.post(
        f"/v1/agents/{agent_id}/invoke",
        json={"capability": "test", "input": {"x": 2}},
        headers={"X-API-Key": api_key},
    )
    assert r5.status_code == 401
