from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db import models

client = TestClient(app)


def test_audit_logs_capture_api_calls(monkeypatch):
    """Test that audit logs capture API calls with proper metadata."""
    # Mock stack auth
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth, "verify_stack_access_token", 
        lambda t: {"id": "user1", "selectedTeamId": "org1"}
    )
    monkeypatch.setattr(
        stack_auth, "verify_team_membership", 
        lambda team, tok: {"id": team}
    )

    # Make an API call that should be audited
    r = client.post(
        "/v1/agents",
        json={"brief": "audit test agent"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]

    # Check that audit log was created
    db = SessionLocal()
    try:
        audit_log = (
            db.query(models.AuditLog)
            .filter(models.AuditLog.org_id == "org1")
            .filter(models.AuditLog.endpoint == "POST /v1/agents")
            .first()
        )
        assert audit_log is not None
        assert audit_log.actor_id == "user1"
        assert audit_log.status_code == 200
        assert audit_log.request_id is not None
    finally:
        db.close()


def test_audit_logs_api_key_auth(monkeypatch):
    """Test that audit logs properly handle API key authentication."""
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth, "verify_stack_access_token", 
        lambda t: {"id": "user1", "selectedTeamId": "org1"}
    )
    monkeypatch.setattr(
        stack_auth, "verify_team_membership", 
        lambda team, tok: {"id": team}
    )

    # Create agent and API key
    r1 = client.post(
        "/v1/agents",
        json={"brief": "api key test"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    agent_id = r1.json()["agent_id"]

    r2 = client.post(
        f"/v1/agents/{agent_id}/keys",
        json={"name": "test-key"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    api_key = r2.json()["api_key"]

    # Use API key to invoke
    r3 = client.post(
        f"/v1/agents/{agent_id}/invoke",
        json={"capability": "test", "input": {"x": 1}},
        headers={"X-API-Key": api_key},
    )
    assert r3.status_code == 200

    # Check audit log for API key usage
    db = SessionLocal()
    try:
        audit_log = (
            db.query(models.AuditLog)
            .filter(models.AuditLog.org_id == "org1")
            .filter(models.AuditLog.endpoint == f"POST /v1/agents/{agent_id}/invoke")
            .first()
        )
        assert audit_log is not None
        assert audit_log.actor_id == "api_key"  # API key auth
        assert audit_log.agent_id == agent_id
        assert audit_log.capability == "test"
        assert audit_log.status_code == 200
    finally:
        db.close()


def test_audit_logs_query_endpoint(monkeypatch):
    """Test the audit logs query endpoint."""
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth, "verify_stack_access_token", 
        lambda t: {"id": "user1", "selectedTeamId": "org1"}
    )
    monkeypatch.setattr(
        stack_auth, "verify_team_membership", 
        lambda team, tok: {"id": team}
    )

    # Make some API calls to generate audit logs
    client.post(
        "/v1/agents",
        json={"brief": "test1"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    client.post(
        "/v1/agents",
        json={"brief": "test2"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )

    # Query audit logs
    r = client.get(
        "/v1/audit/logs?limit=10",
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "logs" in data
    assert len(data["logs"]) >= 2  # At least the two agent creations
    
    # Check log structure
    log = data["logs"][0]
    assert "actor_id" in log
    assert "endpoint" in log
    assert "status_code" in log
    assert "created_at" in log


def test_audit_logs_org_isolation(monkeypatch):
    """Test that audit logs respect org isolation."""
    from app.security import stack_auth

    def mock_verify(token):
        if token == "org1-token":
            return {"id": "user1", "selectedTeamId": "org1"}
        elif token == "org2-token":
            return {"id": "user2", "selectedTeamId": "org2"}
        raise Exception("Invalid token")

    monkeypatch.setattr(stack_auth, "verify_stack_access_token", mock_verify)
    monkeypatch.setattr(stack_auth, "verify_team_membership", lambda team, tok: {"id": team})

    # Create agents in different orgs
    client.post(
        "/v1/agents",
        json={"brief": "org1 agent"},
        headers={"Authorization": "Bearer org1-token", "X-Team-Id": "org1"},
    )
    client.post(
        "/v1/agents",
        json={"brief": "org2 agent"},
        headers={"Authorization": "Bearer org2-token", "X-Team-Id": "org2"},
    )

    # Query logs from org1 - should only see org1 logs
    r1 = client.get(
        "/v1/audit/logs",
        headers={"Authorization": "Bearer org1-token", "X-Team-Id": "org1"},
    )
    assert r1.status_code == 200
    org1_logs = r1.json()["logs"]
    
    # Query logs from org2 - should only see org2 logs
    r2 = client.get(
        "/v1/audit/logs",
        headers={"Authorization": "Bearer org2-token", "X-Team-Id": "org2"},
    )
    assert r2.status_code == 200
    org2_logs = r2.json()["logs"]

    # Verify isolation - no overlap in request IDs
    org1_request_ids = {log["request_id"] for log in org1_logs}
    org2_request_ids = {log["request_id"] for log in org2_logs}
    assert len(org1_request_ids.intersection(org2_request_ids)) == 0
