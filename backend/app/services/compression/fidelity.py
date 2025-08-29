"""
SC.1-06: Fidelity and translation helpers for LSL/ADL/OPL.

Provides dict<->object conversion utilities to support JSON interop and
round‑trip fidelity validation.
"""
from __future__ import annotations
from typing import Dict, Any

from .lsl import CompressedLearningSession, LearningOutcome
from .adl import CompressedAgentBrief
from .opl import CompressedOptimizationTrace


# LSL

def lsl_to_dict(obj: CompressedLearningSession) -> Dict[str, Any]:
    return {
        "iteration": obj.iteration,
        "system": obj.system,
        "outcomes": {
            k: {"code": v[0].value, "confidence": float(v[1])} for k, v in obj.outcomes.items()
        },
        "tests": [obj.tests[0], obj.tests[1]],
        "errors": dict(obj.errors),
    }


def lsl_from_dict(d: Dict[str, Any]) -> CompressedLearningSession:
    outcomes = {k: (LearningOutcome(v["code"]), float(v["confidence"])) for k, v in (d.get("outcomes") or {}).items()}
    tests = tuple(d.get("tests") or (0, 0))
    errors = d.get("errors") or {}
    return CompressedLearningSession(
        iteration=int(d.get("iteration", 0)),
        system=str(d.get("system", "unknown")),
        outcomes=outcomes,
        tests=tests,  # type: ignore[arg-type]
        errors=errors,
    )


# ADL

def adl_to_dict(obj: CompressedAgentBrief) -> Dict[str, Any]:
    return {
        "agent_id": obj.agent_id,
        "role": obj.role,
        "capabilities": dict(obj.capabilities),
        "tools": list(obj.tools),
        "constraints": list(obj.constraints),
        "goals": list(obj.goals),
        "style": obj.style,
    }


def adl_from_dict(d: Dict[str, Any]) -> CompressedAgentBrief:
    return CompressedAgentBrief(
        agent_id=str(d["agent_id"]),
        role=d.get("role"),
        capabilities=dict(d.get("capabilities") or {}),
        tools=list(d.get("tools") or []),
        constraints=list(d.get("constraints") or []),
        goals=list(d.get("goals") or []),
        style=d.get("style"),
    )


# OPL

def opl_to_dict(obj: CompressedOptimizationTrace) -> Dict[str, Any]:
    return {
        "heuristics": list(obj.heuristics),
        "metrics": dict(obj.metrics),
        "exemplars": list(obj.exemplars),
        "params": dict(obj.params),
        "notes": obj.notes,
    }


def opl_from_dict(d: Dict[str, Any]) -> CompressedOptimizationTrace:
    return CompressedOptimizationTrace(
        heuristics=list(d.get("heuristics") or []),
        metrics=dict(d.get("metrics") or {}),
        exemplars=list(d.get("exemplars") or []),
        params=dict(d.get("params") or {}),
        notes=d.get("notes"),
    )

