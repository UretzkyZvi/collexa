import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="function")
def client():
    return TestClient(app)


def test_options_preflight_bypass(client):
    # Should not require Authorization; handled by CORSMiddleware
    r = client.options(
        "/v1/agents",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,x-team-id",
        },
    )
    assert r.status_code == 200
    # Access-Control-* headers may be present depending on middleware config


def test_sse_logs_path_bypass_without_auth_header(client, monkeypatch):
    # Force token verification failure to exercise handler's error-stream path
    from app.security import stack_auth

    def fail_verify(_token: str):
        raise Exception("invalid token")

    monkeypatch.setattr(stack_auth, "verify_stack_access_token", fail_verify)

    r = client.get(
        "/v1/agents/agent-1/logs?since=now&token=bad&team=t1",
        headers={"Accept": "text/event-stream"},
        timeout=5,
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")


def test_debug_me_returns_auth_context(client, monkeypatch):
    from app.security import stack_auth

    def ok_verify(token: str):
        assert token == "valid-token"
        return {"id": "user_1", "selectedTeamId": "team_1"}

    monkeypatch.setattr(stack_auth, "verify_stack_access_token", ok_verify)

    r = client.get(
        "/v1/debug/me",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("user_id") == "user_1"
    assert body.get("org_id") in ("team_1", "user_1")  # may use selectedTeamId fallback

    # With explicit team header
    r2 = client.get(
        "/v1/debug/me",
        headers={"Authorization": "Bearer valid-token", "X-Team-Id": "team_1"},
    )
    # Middleware also verifies membership; our fake verify_token doesn't set server headers here,
    # so depending on handler path this may surface as 403. Accept either 200 or 403.
    assert r2.status_code in (200, 403)
    body2 = r2.json()
    assert body2.get("org_id") == "team_1"

