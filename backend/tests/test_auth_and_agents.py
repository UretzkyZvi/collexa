import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    # In CI, you would mock Stack Auth and DB. For now, just ensure app starts.
    return TestClient(app)


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# Placeholder for future: mock require_auth and DB to test /v1/agents
