from fastapi.testclient import TestClient
from app.main import app
from app.observability.metrics import metrics
from app.observability.logging import get_structured_logger, set_request_context
from app.observability.tracing import tracer, start_span

client = TestClient(app)


def test_metrics_collection(monkeypatch):
    """Test that metrics are collected during API calls."""
    # Mock stack auth
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth,
        "verify_stack_access_token",
        lambda t: {"id": "user1", "selectedTeamId": "org1"},
    )
    monkeypatch.setattr(
        stack_auth, "verify_team_membership", lambda team, tok: {"id": team}
    )

    # Clear metrics
    metrics._counters.clear()
    metrics._histograms.clear()

    # Make API calls
    r1 = client.post(
        "/v1/agents",
        json={"brief": "metrics test"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    assert r1.status_code == 200

    # Check that metrics were recorded
    api_calls = metrics.get_counter("api_calls_total", {"org_id": "org1"})
    assert api_calls >= 1

    duration_stats = metrics.get_histogram_stats(
        "request_duration_ms", {"org_id": "org1"}
    )
    assert duration_stats["count"] >= 1
    assert duration_stats["avg"] > 0


def test_metrics_endpoint(monkeypatch):
    """Test the metrics endpoint returns proper data."""
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth,
        "verify_stack_access_token",
        lambda t: {"id": "user1", "selectedTeamId": "org1"},
    )
    monkeypatch.setattr(
        stack_auth, "verify_team_membership", lambda team, tok: {"id": team}
    )

    # Make some API calls first
    client.post(
        "/v1/agents",
        json={"brief": "test"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )

    # Get metrics
    r = client.get(
        "/v1/metrics",
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    assert r.status_code == 200
    data = r.json()

    assert "org_id" in data
    assert "api_calls" in data
    assert "request_duration_ms" in data
    assert "agent_invocations" in data

    assert data["api_calls"]["total"] >= 0
    assert "success_rate" in data["api_calls"]


def test_structured_logging():
    """Test structured logging functionality."""
    logger = get_structured_logger("test")

    # Set context
    set_request_context("req-123", "org1", "agent-456")

    # This would normally output JSON logs
    logger.info("Test message", extra={"test_field": "test_value"})

    # Test passes if no exceptions are raised


def test_tracing_functionality():
    """Test basic tracing functionality."""
    # Clear previous spans
    tracer.spans.clear()

    # Start a span
    span = start_span("test_operation", operation="test", user_id="user1")
    span.set_attribute("test_attr", "test_value")
    span.finish()

    # Check span was recorded
    spans = tracer.get_spans()
    assert len(spans) >= 1

    test_span = spans[-1]  # Get the last span
    assert test_span.name == "test_operation"
    assert test_span.attributes["operation"] == "test"
    assert test_span.attributes["test_attr"] == "test_value"
    assert test_span.end_time is not None
    assert test_span.duration_ms > 0


def test_agent_invocation_observability(monkeypatch):
    """Test that agent invocations are properly tracked."""
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth,
        "verify_stack_access_token",
        lambda t: {"id": "user1", "selectedTeamId": "org1"},
    )
    monkeypatch.setattr(
        stack_auth, "verify_team_membership", lambda team, tok: {"id": team}
    )

    # Clear metrics
    metrics._counters.clear()
    metrics._histograms.clear()

    # Create agent
    r1 = client.post(
        "/v1/agents",
        json={"brief": "observability test"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    agent_id = r1.json()["agent_id"]

    # Invoke agent
    r2 = client.post(
        f"/v1/agents/{agent_id}/invoke",
        json={"capability": "test", "input": {"x": 1}},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )
    assert r2.status_code == 200

    # Check invocation metrics
    invocation_count = metrics.get_counter(
        "agent_invocations_total", {"org_id": "org1"}
    )
    assert invocation_count >= 1

    invocation_duration = metrics.get_histogram_stats(
        "agent_invocation_duration_ms", {"org_id": "org1"}
    )
    assert invocation_duration["count"] >= 1
    assert invocation_duration["avg"] > 0


def test_request_id_in_response_headers(monkeypatch):
    """Test that X-Request-ID header is added to responses."""
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth,
        "verify_stack_access_token",
        lambda t: {"id": "user1", "selectedTeamId": "org1"},
    )
    monkeypatch.setattr(
        stack_auth, "verify_team_membership", lambda team, tok: {"id": team}
    )

    r = client.post(
        "/v1/agents",
        json={"brief": "request id test"},
        headers={"Authorization": "Bearer user1-token", "X-Team-Id": "org1"},
    )

    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 0
