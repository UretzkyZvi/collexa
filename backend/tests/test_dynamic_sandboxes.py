"""
Tests for dynamic sandbox API endpoints.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.services.sandbox_orchestrator import SandboxInfo, SandboxService
from app.schemas.sandbox import CreateSandboxRequest, ServiceConfigSchema

client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    """Mock Stack Auth and database for all tests."""
    def fake_verify_token(token: str):
        if token == "fake-token":  # Note: without "Bearer " prefix
            return {"id": "test-user", "selectedTeamId": "test_org_123"}
        raise Exception("invalid token")

    def fake_verify_team(team_id: str, token: str):
        if token != "fake-token":  # Note: without "Bearer " prefix
            raise Exception("invalid token")
        if team_id != "test_org_123":
            raise Exception("not a member")
        return {"id": team_id}

    def fake_set_rls(db, org_id):
        # Mock RLS setting - do nothing
        pass

    monkeypatch.setattr(
        "app.security.stack_auth.verify_stack_access_token", fake_verify_token
    )
    monkeypatch.setattr(
        "app.security.stack_auth.verify_team_membership", fake_verify_team
    )
    monkeypatch.setattr(
        "app.db.session.set_rls_for_session", fake_set_rls
    )


@pytest.fixture
def mock_db():
    """Mock database session."""
    from app.db import models

    mock_session = AsyncMock()
    # Mock agent query
    mock_agent = models.Agent()
    mock_agent.id = "agent_456"
    mock_agent.org_id = "test_org_123"
    mock_agent.display_name = "Test Agent"
    mock_session.query.return_value.filter.return_value.first.return_value = mock_agent

    with patch("app.api.deps.get_db", return_value=mock_session):
        yield mock_session


@pytest.fixture
def sample_sandbox_info():
    """Sample sandbox info for testing."""
    return SandboxInfo(
        sandbox_id="sb_test123",
        agent_id="agent_456",
        services={
            "figma": SandboxService(
                container_id="prism_figma_sb_test123",
                port=45001,
                url="http://localhost:45001",
                status="running",
                spec_path="/tmp/sb_test123_figma.yaml",
                endpoints=["/me", "/files/{key}", "/files/{key}/nodes"]
            )
        },
        status="running",
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=2),
        last_accessed=datetime.utcnow(),
        proxy_url="http://localhost:4000/sandbox/sb_test123"
    )


class TestCreateDynamicSandbox:
    """Test dynamic sandbox creation."""
    
    def test_create_sandbox_success(self, mock_db, sample_sandbox_info):
        """Test successful sandbox creation."""
        
        # Mock domain service at the router level
        with patch('app.api.routers.sandboxes.SandboxDomainService') as mock_service_class:
            mock_service = AsyncMock()

            # Convert SandboxInfo to SandboxResponse for the return value
            from app.schemas.sandbox import SandboxResponse, SandboxServiceResponse
            services = {}
            for name, service in sample_sandbox_info.services.items():
                services[name] = SandboxServiceResponse(
                    url=service.url,
                    status=service.status,
                    endpoints=service.endpoints
                )

            sandbox_response = SandboxResponse(
                sandbox_id=sample_sandbox_info.sandbox_id,
                agent_id=sample_sandbox_info.agent_id,
                status=sample_sandbox_info.status,
                services=services,
                proxy_url=sample_sandbox_info.proxy_url,
                created_at=sample_sandbox_info.created_at,
                expires_at=sample_sandbox_info.expires_at,
                last_accessed=sample_sandbox_info.last_accessed
            )

            mock_service.create_sandbox.return_value = sandbox_response
            mock_service_class.return_value = mock_service
            
            response = client.post(
                "/v1/agents/agent_456/sandboxes",
                json={
                    "required_services": ["figma"],
                    "custom_configs": {
                        "figma": {
                            "service_type": "figma",
                            "workspace_config": {
                                "project_name": "Test Project"
                            }
                        }
                    },
                    "ttl_minutes": 120
                },
                headers={
                    "Authorization": "Bearer fake-token",
                    "X-Team-Id": "test_org_123"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["sandbox_id"] == "sb_test123"
            assert data["agent_id"] == "agent_456"
            assert data["status"] == "running"
            assert "figma" in data["services"]
            assert data["services"]["figma"]["url"] == "http://localhost:45001"
            assert data["services"]["figma"]["status"] == "running"
            assert len(data["services"]["figma"]["endpoints"]) == 3
    
    def test_create_sandbox_invalid_request(self, mock_db):
        """Test sandbox creation with invalid request."""

        response = client.post(
            "/v1/agents/agent_456/sandboxes",
            json={
                "required_services": [],  # Empty services should fail validation
                "ttl_minutes": 0  # Invalid TTL
            },
            headers={
                "Authorization": "Bearer fake-token",
                "X-Team-Id": "test_org_123"
            }
        )

        assert response.status_code == 422  # Validation error
    
    def test_create_sandbox_service_error(self, mock_db):
        """Test sandbox creation when service fails."""

        with patch('app.api.routers.sandboxes.SandboxDomainService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.create_sandbox.side_effect = Exception("Docker container failed to start")
            mock_service_class.return_value = mock_service

            response = client.post(
                "/v1/agents/agent_456/sandboxes",
                json={
                    "required_services": ["figma"],
                    "ttl_minutes": 60
                },
                headers={
                    "Authorization": "Bearer fake-token",
                    "X-Team-Id": "test_org_123"
                }
            )

            assert response.status_code == 400
            data = response.json()
            assert "Docker container failed to start" in data["detail"]


class TestGetDynamicSandbox:
    """Test getting sandbox information."""
    
    def test_get_sandbox_success(self, mock_db, sample_sandbox_info):
        """Test successful sandbox retrieval."""

        with patch('app.api.routers.sandboxes.SandboxDomainService') as mock_service_class:
            mock_service = AsyncMock()

            # Convert SandboxInfo to SandboxResponse
            from app.schemas.sandbox import SandboxResponse, SandboxServiceResponse
            services = {}
            for name, service in sample_sandbox_info.services.items():
                services[name] = SandboxServiceResponse(
                    url=service.url,
                    status=service.status,
                    endpoints=service.endpoints
                )

            sandbox_response = SandboxResponse(
                sandbox_id=sample_sandbox_info.sandbox_id,
                agent_id=sample_sandbox_info.agent_id,
                status=sample_sandbox_info.status,
                services=services,
                proxy_url=sample_sandbox_info.proxy_url,
                created_at=sample_sandbox_info.created_at,
                expires_at=sample_sandbox_info.expires_at,
                last_accessed=sample_sandbox_info.last_accessed
            )

            mock_service.get_sandbox.return_value = sandbox_response
            mock_service_class.return_value = mock_service

            response = client.get(
                "/v1/agents/agent_456/sandboxes/sb_test123",
                headers={
                    "Authorization": "Bearer fake-token",
                    "X-Team-Id": "test_org_123"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["sandbox_id"] == "sb_test123"
            assert data["agent_id"] == "agent_456"
            assert "figma" in data["services"]
    
    def test_get_sandbox_not_found(self, mock_db):
        """Test getting non-existent sandbox."""

        with patch('app.api.routers.sandboxes.SandboxDomainService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_sandbox.side_effect = Exception("Sandbox not found")
            mock_service_class.return_value = mock_service

            response = client.get(
                "/v1/agents/agent_456/sandboxes/nonexistent",
                headers={
                    "Authorization": "Bearer fake-token",
                    "X-Team-Id": "test_org_123"
                }
            )

            assert response.status_code == 404
            data = response.json()
            assert "Sandbox not found" in data["detail"]


class TestListDynamicSandboxes:
    """Test listing sandboxes."""
    
    def test_list_sandboxes_success(self, mock_db, sample_sandbox_info):
        """Test successful sandbox listing."""

        from app.schemas.sandbox import SandboxListResponse, SandboxResponse, SandboxServiceResponse

        # Convert SandboxInfo to SandboxResponse
        services = {}
        for name, service in sample_sandbox_info.services.items():
            services[name] = SandboxServiceResponse(
                url=service.url,
                status=service.status,
                endpoints=service.endpoints
            )

        sandbox_response = SandboxResponse(
            sandbox_id=sample_sandbox_info.sandbox_id,
            agent_id=sample_sandbox_info.agent_id,
            status=sample_sandbox_info.status,
            services=services,
            proxy_url=sample_sandbox_info.proxy_url,
            created_at=sample_sandbox_info.created_at,
            expires_at=sample_sandbox_info.expires_at,
            last_accessed=sample_sandbox_info.last_accessed
        )

        mock_response = SandboxListResponse(
            sandboxes=[sandbox_response],
            total=1
        )
        
        with patch('app.api.routers.sandboxes.SandboxDomainService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.list_sandboxes.return_value = mock_response
            mock_service_class.return_value = mock_service

            response = client.get(
                "/v1/agents/agent_456/sandboxes",
                headers={
                    "Authorization": "Bearer fake-token",
                    "X-Team-Id": "test_org_123"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["sandboxes"]) == 1
            assert data["sandboxes"][0]["sandbox_id"] == "sb_test123"


class TestUpdateDynamicSandbox:
    """Test updating sandbox configuration."""
    
    def test_update_sandbox_add_service(self, mock_db, sample_sandbox_info):
        """Test adding a service to existing sandbox."""
        
        # Update sample to include slack service
        sample_sandbox_info.services["slack"] = SandboxService(
            container_id="prism_slack_sb_test123",
            port=45002,
            url="http://localhost:45002",
            status="running",
            spec_path="/tmp/sb_test123_slack.yaml",
            endpoints=["/auth.test", "/chat.postMessage"]
        )
        
        with patch('app.api.routers.sandboxes.SandboxDomainService') as mock_service_class:
            mock_service = AsyncMock()

            # Convert SandboxInfo to SandboxResponse
            from app.schemas.sandbox import SandboxResponse, SandboxServiceResponse
            services = {}
            for name, service in sample_sandbox_info.services.items():
                services[name] = SandboxServiceResponse(
                    url=service.url,
                    status=service.status,
                    endpoints=service.endpoints
                )

            sandbox_response = SandboxResponse(
                sandbox_id=sample_sandbox_info.sandbox_id,
                agent_id=sample_sandbox_info.agent_id,
                status=sample_sandbox_info.status,
                services=services,
                proxy_url=sample_sandbox_info.proxy_url,
                created_at=sample_sandbox_info.created_at,
                expires_at=sample_sandbox_info.expires_at,
                last_accessed=sample_sandbox_info.last_accessed
            )

            mock_service.update_sandbox.return_value = sandbox_response
            mock_service_class.return_value = mock_service

            response = client.patch(
                "/v1/agents/agent_456/sandboxes/sb_test123",
                json={
                    "add_services": ["slack"],
                    "update_configs": {
                        "slack": {
                            "service_type": "slack",
                            "workspace_config": {
                                "team_name": "Test Team"
                            }
                        }
                    }
                },
                headers={
                    "Authorization": "Bearer fake-token",
                    "X-Team-Id": "test_org_123"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert "slack" in data["services"]
            assert data["services"]["slack"]["url"] == "http://localhost:45002"


class TestDeleteDynamicSandbox:
    """Test deleting sandbox."""
    
    def test_delete_sandbox_success(self, mock_db):
        """Test successful sandbox deletion."""
        
        from app.schemas.sandbox import DeleteSandboxResponse
        
        mock_response = DeleteSandboxResponse(
            message="Sandbox deleted successfully",
            sandbox_id="sb_test123"
        )
        
        with patch('app.api.routers.sandboxes.SandboxDomainService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.delete_sandbox.return_value = mock_response
            mock_service_class.return_value = mock_service

            response = client.delete(
                "/v1/agents/agent_456/sandboxes/sb_test123",
                headers={
                    "Authorization": "Bearer fake-token",
                    "X-Team-Id": "test_org_123"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Sandbox deleted successfully"
            assert data["sandbox_id"] == "sb_test123"
    
    def test_delete_sandbox_not_found(self, mock_db):
        """Test deleting non-existent sandbox."""

        with patch('app.api.routers.sandboxes.SandboxDomainService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.delete_sandbox.side_effect = Exception("Sandbox not found")
            mock_service_class.return_value = mock_service

            response = client.delete(
                "/v1/agents/agent_456/sandboxes/nonexistent",
                headers={
                    "Authorization": "Bearer fake-token",
                    "X-Team-Id": "test_org_123"
                }
            )

            assert response.status_code == 404
            data = response.json()
            assert "Sandbox not found" in data["detail"]
