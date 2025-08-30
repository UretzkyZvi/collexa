from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _mock_auth(monkeypatch):
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth,
        "verify_stack_access_token",
        lambda t: {"id": "u1", "selectedTeamId": "o1"},
    )
    monkeypatch.setattr(stack_auth, "verify_team_membership", lambda team, tok: {"id": team})


def test_preview_builder_validate(monkeypatch):
    _mock_auth(monkeypatch)
    resp = client.post(
        "/v1/agents/builder/preview",
        json={"brief": "ux designer", "validate": True},
        headers={"Authorization": "Bearer t", "X-Team-Id": "o1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["blueprint"]["adl_version"] == "v1"
    assert data["validation"]["status"] == "ok"


def test_create_builder(monkeypatch):
    _mock_auth(monkeypatch)
    resp = client.post(
        "/v1/agents/builder/create",
        json={"brief": "ux designer"},
        headers={"Authorization": "Bearer t", "X-Team-Id": "o1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "agent_id" in data
    assert data["blueprint"]["adl_version"] == "v1"

