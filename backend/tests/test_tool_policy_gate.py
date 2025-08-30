import types
import pytest

from app.services.learning.tools.base import policy_gate
from app.services.learning.tools import base as tools_base


def test_policy_gate_mock_mode_allowlist():
    # http GET/POST allowed; fs read/write allowed; ws/graphql/search allowed; others denied
    assert policy_gate("http", "GET", "mock", {}) is True
    assert policy_gate("http", "POST", "mock", {}) is True
    assert policy_gate("fs", "read", "mock", {}) is True
    assert policy_gate("fs", "write", "mock", {}) is True
    assert policy_gate("ws", "connect", "mock", {}) is True
    assert policy_gate("graphql", "query", "mock", {}) is True
    assert policy_gate("search", "query", "mock", {}) is True
    # Unknown tool/action should be denied in mock
    assert policy_gate("docker", "run", "mock", {}) is False


def test_policy_gate_non_mock_denies_without_evaluator(monkeypatch):
    # Ensure no evaluator is registered
    monkeypatch.setattr(tools_base, "_policy_evaluator", None, raising=False)
    assert policy_gate("http", "GET", "connected", {}) is False
    assert policy_gate("fs", "read", "emulated", {}) is False


def test_policy_gate_respects_pluggable_evaluator(monkeypatch):
    # Register a simple evaluator that allows only graphql queries
    def fake_eval(tool, action, mode, ctx):
        return tool == "graphql" and action == "query" and mode in {"emulated", "connected"}

    monkeypatch.setattr(tools_base, "_policy_evaluator", fake_eval, raising=False)

    assert policy_gate("graphql", "query", "connected", {"agent_id": "a1"}) is True
    assert policy_gate("http", "GET", "connected", {"agent_id": "a1"}) is False

    # Reset evaluator
    monkeypatch.setattr(tools_base, "_policy_evaluator", None, raising=False)

