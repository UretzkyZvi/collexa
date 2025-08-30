from __future__ import annotations

from typing import List, Dict, Any, Tuple
from pydantic import ValidationError

from app.schemas.agent_blueprint import AgentBlueprintV1, InstructionsPack
from app.services.capability_naming import capability_key
from app.services.learning.tools.registry import ToolRegistry


def parse_brief_to_adl(agent_id: str, brief: str) -> AgentBlueprintV1:
    # Minimal heuristic v0: extract role from brief first phrase
    role = (brief or "agent").split(" ")[0].lower()
    bp = AgentBlueprintV1(agent_id=agent_id, role=role)
    # Defaults: goals/constraints can be expanded later
    bp.goals = []
    bp.constraints = []
    return bp


def select_capability_kit(bp: AgentBlueprintV1) -> Tuple[List[str], List[str]]:
    registry = ToolRegistry()
    tool_names: List[str] = []
    cap_keys: List[str] = []
    # Simple strategy: include core safe tools for MVP
    for t in registry.tools:
        name = getattr(t, "name", None) or t.__class__.__name__.replace("Tool", "").lower()
        tool_names.append(name)
        # Default actions per tool (MVP)
        default_actions = {
            "http": ["get", "post"],
            "fs": ["read", "write"],
            "graphql": ["query"],
            "ws": ["connect"],
            "search": ["query"],
        }.get(name, ["use"])  # fallback "use"
        for act in default_actions:
            cap_keys.append(capability_key(name, act))

    return tool_names, cap_keys


def render_instructions(bp: AgentBlueprintV1, tool_names: List[str]) -> InstructionsPack:
    system = f"You are a specialized {bp.role} agent. Use tools: {', '.join(tool_names)}."
    developer = "Follow safety policies and operate in mock mode by default."
    examples: List[Dict[str, Any]] = [{"input": "hello", "output": {"echo": "hello"}}]
    return InstructionsPack(system=system, developer=developer, examples=examples)


def produce_manifest(capability_keys: List[str]) -> Dict[str, Any]:
    # MVP: unsigned manifest structure compatible with H.1 signing later
    return {"version": "v1", "capabilities": capability_keys}

