import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="function")
def client():
    return TestClient(app)

@pytest.fixture
def fake_auth(monkeypatch):
    from app.api import deps
    async def fake_require_team(*args, **kwargs):
        return {"user_id": "u1", "org_id": "o1"}
    async def fake_require_auth(*args, **kwargs):
        return {"user_id": "u1", "org_id": "o1"}
    monkeypatch.setattr(deps, "require_team", fake_require_team)
    monkeypatch.setattr(deps, "require_auth", fake_require_auth)


def test_invoke_persists_logs_and_output_ordered(client, fake_auth):
    # Create agent
    r = client.post("/v1/agents", json={"brief": "test"}, headers={"X-Team-Id": "o1", "Authorization": "Bearer fake"})
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]

    # Invoke
    payload = {"capability": "c1", "input": {"x": 1}}
    r2 = client.post(f"/v1/agents/{agent_id}/invoke", json=payload, headers={"X-Team-Id": "o1", "Authorization": "Bearer fake"})
    assert r2.status_code == 200
    run_id = r2.json()["run_id"]
    assert r2.json()["result"]["echo"] == payload

    # Fetch logs
    gl = client.get(f"/v1/runs/{run_id}/logs", headers={"Authorization": "Bearer fake"})
    assert gl.status_code == 200
    logs = gl.json()
    assert len(logs) >= 2
    # Order ascending by ts
    ts_list = [l["ts"] for l in logs]
    assert ts_list == sorted(ts_list)
    # Last message should include complete output string
    assert any("complete" in l["message"] for l in logs)


def test_sse_per_run_emits_log_and_complete(client, fake_auth):
    # Create agent & invoke to push events
    r = client.post("/v1/agents", json={"brief": "t"}, headers={"X-Team-Id": "o1", "Authorization": "Bearer fake"})
    agent_id = r.json()["agent_id"]
    r2 = client.post(f"/v1/agents/{agent_id}/invoke", json={"capability": "c", "input": {}}, headers={"X-Team-Id": "o1", "Authorization": "Bearer fake"})
    run_id = r2.json()["run_id"]

    # Stream SSE
    with client.stream("GET", f"/v1/runs/{run_id}/stream") as resp:
        assert resp.status_code == 200
        seen_types = set()
        for _ in range(10):
            line = resp.iter_lines().__next__()
            if not line:
                continue
            if line.startswith(b"data: "):
                data = line[len(b"data: "):]
                try:
                    obj = json.loads(data)
                    t = obj.get("type")
                    if t:
                        seen_types.add(t)
                    if "complete" in seen_types and "log" in seen_types:
                        break
                except Exception:
                    pass
        assert "log" in seen_types and "complete" in seen_types

