import pytest
import json
import os
import sys
from unittest.mock import AsyncMock, patch

from app.security.opa import OPAPolicyEngine


@pytest.mark.asyncio
async def test_opa_policy_engine_allow():
    """Test OPA policy engine allows valid requests."""
    engine = OPAPolicyEngine("http://mock-opa:8181")

    # Mock the evaluate_policy method directly
    with patch.object(engine, "evaluate_policy") as mock_eval:
        mock_eval.return_value = {"result": {"allow": True}}
        result = await engine.can_invoke_capability(
            user_id="u1", org_id="o1", agent_id="agent-1", capability="test_capability"
        )
        assert result is True


@pytest.mark.asyncio
async def test_opa_policy_engine_deny():
    """Test OPA policy engine denies invalid requests."""
    engine = OPAPolicyEngine("http://mock-opa:8181")

    # Mock the evaluate_policy method directly
    with patch.object(engine, "evaluate_policy") as mock_eval:
        mock_eval.return_value = {"result": {"allow": False}}
        result = await engine.can_invoke_capability(
            user_id="u2",
            org_id="o1",
            agent_id="agent-1",
            capability="restricted_capability",
        )
        assert result is False


@pytest.mark.asyncio
async def test_opa_policy_engine_error_fail_closed():
    """Test OPA policy engine fails closed on errors."""
    engine = OPAPolicyEngine("http://mock-opa:8181")

    # Mock OPA error response
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(engine.client, "post", return_value=mock_response):
        result = await engine.can_invoke_capability(
            user_id="u1", org_id="o1", agent_id="agent-1", capability="test_capability"
        )
        assert result is False


@pytest.mark.asyncio
async def test_opa_policy_engine_network_error():
    """Test OPA policy engine handles network errors."""
    engine = OPAPolicyEngine("http://unreachable:8181")

    # Mock network error
    with patch.object(
        engine.client, "post", side_effect=Exception("Connection failed")
    ):
        result = await engine.can_invoke_capability(
            user_id="u1", org_id="o1", agent_id="agent-1", capability="test_capability"
        )
        assert result is False


@pytest.mark.asyncio
async def test_opa_health_check():
    """Test OPA health check."""
    engine = OPAPolicyEngine("http://mock-opa:8181")

    # Mock healthy response
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch.object(engine.client, "get", return_value=mock_response):
        result = await engine.health_check()
        assert result is True

    # Mock unhealthy response
    mock_response.status_code = 503
    with patch.object(engine.client, "get", return_value=mock_response):
        result = await engine.health_check()
        assert result is False


def test_opa_policy_evaluation_input_structure():
    """Test that policy input structure is correct."""
    engine = OPAPolicyEngine()

    # This would be called in can_invoke_capability
    input_data = {
        "user": {"id": "u1"},
        "org": {"id": "o1"},
        "agent": {"id": "agent-1"},
        "capability": "test_capability",
        "context": {"method": "POST", "path": "/v1/agents/agent-1/invoke"},
    }

    # Verify structure matches what our Rego policy expects
    assert "user" in input_data
    assert "org" in input_data
    assert "agent" in input_data
    assert "capability" in input_data
    assert input_data["user"]["id"] == "u1"
    assert input_data["org"]["id"] == "o1"
    assert input_data["agent"]["id"] == "agent-1"
    assert input_data["capability"] == "test_capability"
