import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.db import models


client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_stack_auth(monkeypatch):
    """Mock Stack Auth for all tests."""
    def fake_verify_token(token: str):
        if token == "Bearer fake-token":
            return {"id": "test-user", "selectedTeamId": "test-org"}
        raise Exception("invalid token")

    def fake_verify_team(team_id: str, token: str):
        if token != "Bearer fake-token":
            raise Exception("invalid token")
        if team_id != "test-org":
            raise Exception("not a member")
        return {"id": team_id}

    monkeypatch.setattr(
        "app.security.stack_auth.verify_stack_access_token", fake_verify_token
    )
    monkeypatch.setattr(
        "app.security.stack_auth.verify_team_membership", fake_verify_team
    )


def test_create_sandbox_requires_auth():
    """Test that creating a sandbox requires authentication."""
    response = client.post("/v1/agents/test-agent/sandboxes", json={"mode": "mock"})
    assert response.status_code == 401


def test_create_sandbox_mock_mode(mock_auth, mock_db):
    """Test creating a sandbox in mock mode."""
    # Mock agent exists
    mock_agent = models.Agent(id="test-agent", org_id="test-org", display_name="Test agent")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_agent
    
    # Mock sandbox service
    with patch('app.api.routers.sandboxes.SandboxService') as mock_service:
        mock_service_instance = AsyncMock()
        mock_service.return_value = mock_service_instance
        
        response = client.post(
            "/v1/agents/test-agent/sandboxes",
            json={
                "mode": "mock",
                "target_system": "figma",
                "config": {"api_version": "v1"}
            },
            headers={"Authorization": "Bearer fake-token", "X-Team-Id": "test-org"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "mock"
    assert data["target_system"] == "figma"
    assert "sandbox_id" in data
    assert "endpoints" in data
    assert data["endpoints"]["mock_api"].startswith("http://localhost:4010/")


def test_create_sandbox_unsupported_mode(mock_auth, mock_db):
    """Test that unsupported modes are rejected."""
    # Mock agent exists
    mock_agent = models.Agent(id="test-agent", org_id="test-org", display_name="Test agent")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_agent
    
    response = client.post(
        "/v1/agents/test-agent/sandboxes",
        json={"mode": "connected"},  # Not supported in N.1
        headers={"Authorization": "Bearer fake-token", "X-Team-Id": "test-org"}
    )
    
    assert response.status_code == 400
    assert "Only mock mode is supported" in response.json()["detail"]


def test_create_sandbox_agent_not_found(mock_auth, mock_db):
    """Test creating sandbox for non-existent agent."""
    # Mock agent not found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.post(
        "/v1/agents/nonexistent/sandboxes",
        json={"mode": "mock"},
        headers={"Authorization": "Bearer fake-token", "X-Team-Id": "test-org"}
    )
    
    assert response.status_code == 404
    assert "Agent not found" in response.json()["detail"]


def test_list_sandboxes(mock_auth, mock_db):
    """Test listing sandboxes for an agent."""
    # Mock agent exists
    mock_agent = models.Agent(id="test-agent", org_id="test-org", display_name="Test agent")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_agent
    
    # Mock sandboxes
    mock_sandbox = models.Sandbox(
        id="sandbox-1",
        agent_id="test-agent",
        org_id="test-org",
        mode="mock",
        target_system="figma",
        status="running"
    )
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_sandbox]
    
    response = client.get(
        "/v1/agents/test-agent/sandboxes",
        headers={"Authorization": "Bearer fake-token", "X-Team-Id": "test-org"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "sandboxes" in data
    assert len(data["sandboxes"]) == 1
    assert data["sandboxes"][0]["sandbox_id"] == "sandbox-1"
    assert data["sandboxes"][0]["mode"] == "mock"


def test_get_sandbox_details(mock_auth, mock_db):
    """Test getting sandbox details with recent runs."""
    # Mock sandbox exists
    mock_sandbox = models.Sandbox(
        id="sandbox-1",
        agent_id="test-agent",
        org_id="test-org",
        mode="mock",
        target_system="figma",
        status="running",
        config_json={"api_version": "v1"}
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_sandbox
    
    # Mock recent runs
    mock_run = models.SandboxRun(
        id="run-1",
        sandbox_id="sandbox-1",
        phase="learn",
        task_name="explore_endpoints",
        status="completed"
    )
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_run]
    
    response = client.get(
        "/v1/agents/test-agent/sandboxes/sandbox-1",
        headers={"Authorization": "Bearer fake-token", "X-Team-Id": "test-org"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["sandbox_id"] == "sandbox-1"
    assert data["mode"] == "mock"
    assert data["target_system"] == "figma"
    assert data["config"]["api_version"] == "v1"
    assert len(data["recent_runs"]) == 1
    assert data["recent_runs"][0]["run_id"] == "run-1"
    assert data["recent_runs"][0]["phase"] == "learn"


def test_reset_sandbox(mock_auth, mock_db):
    """Test resetting a sandbox."""
    # Mock sandbox exists
    mock_sandbox = models.Sandbox(
        id="sandbox-1",
        agent_id="test-agent",
        org_id="test-org",
        mode="mock",
        status="running"
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_sandbox
    
    # Mock sandbox service
    with patch('app.api.routers.sandboxes.SandboxService') as mock_service:
        mock_service_instance = AsyncMock()
        mock_service.return_value = mock_service_instance
        
        response = client.post(
            "/v1/agents/test-agent/sandboxes/sandbox-1/reset",
            headers={"Authorization": "Bearer fake-token", "X-Team-Id": "test-org"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Sandbox reset successfully"
    assert data["sandbox_id"] == "sandbox-1"
    mock_service_instance.reset_sandbox.assert_called_once_with("sandbox-1")


def test_delete_sandbox(mock_auth, mock_db):
    """Test deleting a sandbox."""
    # Mock sandbox exists
    mock_sandbox = models.Sandbox(
        id="sandbox-1",
        agent_id="test-agent",
        org_id="test-org",
        mode="mock",
        status="running"
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_sandbox
    
    # Mock sandbox service
    with patch('app.api.routers.sandboxes.SandboxService') as mock_service:
        mock_service_instance = AsyncMock()
        mock_service.return_value = mock_service_instance
        
        response = client.delete(
            "/v1/agents/test-agent/sandboxes/sandbox-1",
            headers={"Authorization": "Bearer fake-token", "X-Team-Id": "test-org"}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Sandbox deleted successfully"
    assert data["sandbox_id"] == "sandbox-1"
    mock_service_instance.stop_sandbox.assert_called_once_with("sandbox-1")
    mock_db.delete.assert_called_once_with(mock_sandbox)


def test_list_sandbox_runs(mock_auth, mock_db):
    """Test listing sandbox runs with pagination."""
    # Mock sandbox exists
    mock_sandbox = models.Sandbox(
        id="sandbox-1",
        agent_id="test-agent",
        org_id="test-org",
        mode="mock",
        status="running"
    )
    mock_db.query.return_value.filter.return_value.first.return_value = mock_sandbox
    
    # Mock runs
    mock_run = models.SandboxRun(
        id="run-1",
        sandbox_id="sandbox-1",
        phase="learn",
        task_name="explore_endpoints",
        status="completed",
        input_json={"task": "explore"},
        output_json={"endpoints_found": 5}
    )
    mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_run]
    mock_db.query.return_value.filter.return_value.count.return_value = 1
    
    response = client.get(
        "/v1/agents/test-agent/sandboxes/sandbox-1/runs?limit=10&offset=0",
        headers={"Authorization": "Bearer fake-token", "X-Team-Id": "test-org"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert "pagination" in data
    assert len(data["runs"]) == 1
    assert data["runs"][0]["run_id"] == "run-1"
    assert data["runs"][0]["input"]["task"] == "explore"
    assert data["runs"][0]["output"]["endpoints_found"] == 5
    assert data["pagination"]["total"] == 1
