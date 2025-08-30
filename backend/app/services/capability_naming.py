"""
Capability naming helpers linking ToolRegistry ↔ A2A manifests ↔ OPA policy keys.

Canonical capability key format: "tool:{tool_name}:{action}" (lowercase).
"""
from __future__ import annotations

from typing import Literal


def normalize_action(action: str) -> str:
    a = action.strip().lower()
    # Normalize common HTTP verbs and tool actions
    mapping = {
        "get": "get",
        "post": "post",
        "put": "put",
        "delete": "delete",
        "patch": "patch",
        "read": "read",
        "write": "write",
        "query": "query",
        "connect": "connect",
    }
    # strip punctuation if present
    a = a.replace(" ", "").replace("/", "").replace("\\", "")
    return mapping.get(a, a)


def capability_key(tool_name: str, action: str) -> str:
    return f"tool:{tool_name.strip().lower()}:{normalize_action(action)}"

