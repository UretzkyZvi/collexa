import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_learning_iteration_records_recent_and_metrics(monkeypatch):
    # Run a dev iteration in mock mode and ensure recent LSL is populated
    client = TestClient(app)

    agent_id = "agent_metrics"
    body = {"tasks": ["http request"], "docs": [], "sandbox_mode": "mock"}

    r = client.post(f"/dev/learning/{agent_id}/iterate", json=body)
    assert r.status_code == 200

    # Fetch recent
    r2 = client.get(f"/dev/learning/{agent_id}/recent")
    assert r2.status_code == 200
    data = r2.json()
    assert data["agent_id"] == agent_id
    assert data["tests"]["total"] == 1


def test_policy_gate_non_mock_defaults(monkeypatch):
    # Ensure non-mock mode denies without evaluator wired (safety)
    from app.services.learning.tools.base import policy_gate
    assert policy_gate("http", "GET", "connected", {}) is False

