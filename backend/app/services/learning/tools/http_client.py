"""
HTTP client tool (mock-focused) for N.2 learning loop.

Provides a minimal interface suitable for mock/emulated mode without adding
external dependencies. For connected mode and richer features, swap to httpx.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .base import Tool, ToolSpec, ToolResult, policy_gate


@dataclass
class HttpClientTool:
    spec: ToolSpec = field(default_factory=lambda: ToolSpec(
        name="http",
        category="http",
        description="HTTP client for REST API calls (mock/emulated)",
    ))

    def can_handle(self, task: str) -> bool:
        return any(k in task.lower() for k in ("http", "api", "rest", "get ", "post "))

    def invoke(self, task: str, context: Dict[str, Any], sandbox_mode: str) -> ToolResult:
        # Expect context to carry: method, url, headers, body. In mock mode, we only
        # echo/validate inputs to simulate behavior.
        method = (context.get("method") or "GET").upper()
        url = str(context.get("url") or "")
        if not policy_gate(self.spec.name, method, sandbox_mode, context):
            return ToolResult(False, data=None, errors={"policy_denied": 1})

        # Minimal simulation: return back the request as response
        resp = {
            "status_code": 200,
            "json": context.get("json"),
            "text": context.get("text"),
            "url": url,
            "method": method,
        }
        return ToolResult(True, data=resp, meta={"mode": sandbox_mode})

