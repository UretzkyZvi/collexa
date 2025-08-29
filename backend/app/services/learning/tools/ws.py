"""
WebSocket tool (mock) for N.2 learning loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .base import Tool, ToolSpec, ToolResult, policy_gate


@dataclass
class WebSocketTool:
    spec: ToolSpec = field(default_factory=lambda: ToolSpec(
        name="ws",
        category="realtime",
        description="WebSocket client (mock echo)",
    ))

    def can_handle(self, task: str) -> bool:
        return any(k in task.lower() for k in ("websocket", "ws", "socket"))

    def invoke(self, task: str, context: Dict[str, Any], sandbox_mode: str) -> ToolResult:
        if not policy_gate(self.spec.name, "connect", sandbox_mode, context):
            return ToolResult(False, data=None, errors={"policy_denied": 1})
        message = context.get("message") or "ping"
        return ToolResult(True, data={"echo": message, "status": "connected"})

