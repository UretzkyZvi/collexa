"""
Search tool (mock) for N.2 learning loop: web/doc/code search stubs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .base import Tool, ToolSpec, ToolResult, policy_gate


@dataclass
class SearchTool:
    spec: ToolSpec = field(default_factory=lambda: ToolSpec(
        name="search",
        category="search",
        description="Search APIs (mock results)",
    ))

    def can_handle(self, task: str) -> bool:
        return any(k in task.lower() for k in ("search", "find", "lookup", "docs"))

    def invoke(self, task: str, context: Dict[str, Any], sandbox_mode: str) -> ToolResult:
        if not policy_gate(self.spec.name, "query", sandbox_mode, context):
            return ToolResult(False, data=None, errors={"policy_denied": 1})
        q = context.get("q") or task
        results = [
            {"title": "Result 1", "url": "http://example.local/1", "snippet": f"Snippet for {q}"},
            {"title": "Result 2", "url": "http://example.local/2", "snippet": f"Another snippet for {q}"},
        ]
        return ToolResult(True, data={"query": q, "results": results})

