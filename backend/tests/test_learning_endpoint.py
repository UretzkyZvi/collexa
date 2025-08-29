from fastapi.testclient import TestClient
from app.main import app
from app.api.routers.learning import record_recent_learning
from app.api.deps import require_team


def test_dev_learning_recent_endpoint_roundtrip():
    # Override auth to avoid dealing with bearer tokens/team headers in tests
    app.dependency_overrides[require_team] = lambda: {
        "user_id": "u_test",
        "org_id": "org_test",
        "profile": {"auth": "api_key"},
        "access_token": "",
    }

    client = TestClient(app)

    agent_id = "agentX"
    record_recent_learning(
        agent_id,
        {
            "iteration": 3,
            "system": "FastAPI",
            "outcomes": {
                "routing": {"code": "L", "confidence": 0.8},
                "Depends": {"code": "D", "confidence": 0.9},
            },
            "tests": (10, 12),
            "errors": {"auth": 2},
        },
    )

    resp = client.get(f"/dev/learning/{agent_id}/recent")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["agent_id"] == agent_id
    assert payload["iteration"] == 3
    assert payload["system"] == "FastAPI"
    assert payload["tests"]["passed"] == 10
    assert payload["tests"]["total"] == 12
    assert payload["errors"]["auth"] == 2
    assert payload["outcomes"]["routing"]["code"] == "L"

