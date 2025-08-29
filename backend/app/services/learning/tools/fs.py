"""
Filesystem tool (mock-focused) for N.2 learning loop.

Supports safe read/write to a temp workspace and denies destructive ops in mock
mode. No external deps.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict

from .base import Tool, ToolSpec, ToolResult, policy_gate


@dataclass
class FileSystemTool:
    base_dir: str | None = None
    spec: ToolSpec = field(default_factory=lambda: ToolSpec(
        name="fs",
        category="filesystem",
        description="Filesystem read/write in sandbox temp directory",
    ))

    def _ensure_base(self) -> str:
        if not self.base_dir:
            self.base_dir = tempfile.mkdtemp(prefix="learn_fs_")
        return self.base_dir

    def can_handle(self, task: str) -> bool:
        return any(k in task.lower() for k in ("file", "fs", "read", "write", "save"))

    def invoke(self, task: str, context: Dict[str, Any], sandbox_mode: str) -> ToolResult:
        action = str(context.get("action") or "read").lower()
        path = str(context.get("path") or "")
        if not policy_gate(self.spec.name, action, sandbox_mode, context):
            return ToolResult(False, data=None, errors={"policy_denied": 1})

        base = self._ensure_base()
        abs_path = os.path.abspath(os.path.join(base, path))
        if not abs_path.startswith(base):
            return ToolResult(False, data=None, errors={"path_escape": 1})

        if action == "read":
            if not os.path.exists(abs_path):
                return ToolResult(False, data=None, errors={"not_found": 1})
            with open(abs_path, "r", encoding="utf-8") as f:
                return ToolResult(True, data=f.read(), meta={"path": abs_path})

        if action == "write":
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            data = context.get("data") or ""
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(str(data))
            return ToolResult(True, data={"path": abs_path, "bytes": len(str(data))})

        return ToolResult(False, data=None, errors={"unsupported_action": 1})

