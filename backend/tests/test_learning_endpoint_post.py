from fastapi.testclient import TestClient
from app.main import app


def test_dev_learning_post_and_get_recent():
    client = TestClient(app)
    agent_id = "agentP"

    body = {
        "iteration": 5,
        "system": "FastAPI",
        "outcomes": {
            "routing": {"code": "L", "confidence": 0.91},
            "Depends": {"code": "D", "confidence": 0.88},
        },
        "tests": [11, 12],
        "errors": {"auth": 1},
    }

    post = client.post(f"/dev/learning/{agent_id}/recent", json=body)
    assert post.status_code == 200

    get = client.get(f"/dev/learning/{agent_id}/recent")
    assert get.status_code == 200
    data = get.json()
    assert data["iteration"] == 5
    assert data["tests"]["passed"] == 11 and data["tests"]["total"] == 12
    assert data["outcomes"]["routing"]["code"] == "L"

