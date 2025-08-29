"""
GraphQL tool (mock) for N.2 learning loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .base import Tool, ToolSpec, ToolResult, policy_gate


@dataclass
class GraphQLTool:
    spec: ToolSpec = field(default_factory=lambda: ToolSpec(
        name="graphql",
        category="api",
        description="GraphQL client (mock)",
    ))

    def can_handle(self, task: str) -> bool:
        return "graphql" in task.lower()

    def invoke(self, task: str, context: Dict[str, Any], sandbox_mode: str) -> ToolResult:
        if not policy_gate(self.spec.name, "query", sandbox_mode, context):
            return ToolResult(False, data=None, errors={"policy_denied": 1})
        query = context.get("query") or "{ __typename }"
        variables = context.get("variables") or {}
        # Mock response
        return ToolResult(True, data={"data": {"__typename": "Mock"}, "echo": {"query": query, "variables": variables}})

