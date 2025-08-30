"""
Tooling base interfaces for N.2 learning loop.

Design goals:
- Safe-by-default: tools enforce sandbox mode constraints
- Deterministic: inputs/outputs are serializable for future Temporal replay
- MCP-ready: metadata included to map to MCP tool descriptors later
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol


@dataclass
class ToolSpec:
    name: str
    category: str  # e.g., http, fs, playwright, docker
    description: str
    modes: tuple[str, ...] = ("mock", "emulated", "connected")


@dataclass
class ToolResult:
    success: bool
    data: Any
    errors: Dict[str, int] | None = None
    meta: Dict[str, Any] | None = None


class Tool(Protocol):
    spec: ToolSpec

    def can_handle(self, task: str) -> bool:
        ...

    def invoke(self, task: str, context: Dict[str, Any], sandbox_mode: str) -> ToolResult:
        ...


_policy_evaluator: Optional[Callable[[str, str, str, Dict[str, Any]], bool]] = None


def set_policy_evaluator(fn: Callable[[str, str, str, Dict[str, Any]], bool]) -> None:
    global _policy_evaluator
    _policy_evaluator = fn


def policy_gate(tool_name: str, action: str, sandbox_mode: str, context: Dict[str, Any]) -> bool:
    """Policy gate for tool invocations.

    - In mock mode, default to deny except allow-listed local actions.
    - If a policy evaluator is registered (e.g., OPA), delegate the decision.
    - In non-mock modes, fail-closed (deny) when no evaluator is configured.
    """
    # Delegation to pluggable evaluator (e.g., OPA sync adapter)
    if _policy_evaluator is not None:
        try:
            return bool(_policy_evaluator(tool_name, action, sandbox_mode, context))
        except Exception:
            return False

    if sandbox_mode == "mock":
        # Allow only explicitly safe actions; mock tools are stubbed internally.
        if tool_name == "http" and action in {"GET", "POST"}:
            return True
        if tool_name == "fs" and action in {"read", "write"}:
            return True
        if tool_name in {"ws", "graphql", "search"}:
            return True  # mocked by design
        # Disallow everything else in mock mode by default
        return False

    # Non-mock (emulated/connected): no evaluator configured -> deny by default
    return False

