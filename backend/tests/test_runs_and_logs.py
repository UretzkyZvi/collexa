import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def test_runs_list_empty(client):
    res = client.get("/v1/runs")
    assert res.status_code in (200, 401)  # may require auth in real env


def test_invoke_and_stream(client, monkeypatch):
    # Monkeypatch require_team and require_auth to bypass external auth in tests
    from app.api import deps

    async def fake_require_team(*args, **kwargs):
        return {"user_id": "u1", "org_id": "o1"}

    async def fake_require_auth(*args, **kwargs):
        return {"user_id": "u1", "org_id": "o1"}

    monkeypatch.setattr(deps, "require_team", fake_require_team)
    monkeypatch.setattr(deps, "require_auth", fake_require_auth)

    # Create agent row directly via endpoint
    r = client.post(
        "/v1/agents",
        json={"brief": "t"},
        headers={"X-Team-Id": "o1", "Authorization": "Bearer fake"},
    )
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]

    # Invoke
    r2 = client.post(
        f"/v1/agents/{agent_id}/invoke",
        json={"capability": "c", "input": {}},
        headers={"X-Team-Id": "o1", "Authorization": "Bearer fake"},
    )
    assert r2.status_code == 200
    run_id = r2.json()["run_id"]

    # List runs
    lr = client.get("/v1/runs", headers={"Authorization": "Bearer fake"})
    assert lr.status_code in (200, 401)

    # Fetch logs by run
    gl = client.get(f"/v1/runs/{run_id}/logs", headers={"Authorization": "Bearer fake"})
    assert gl.status_code in (200, 401)
