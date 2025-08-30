"""
Agent Blueprint schemas for AB.1 (ADL v1 + Instructions Pack).

These models define the minimal canonical structure for a generated agent
blueprint and its instruction artifacts, building on SC.1 ADL concepts.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class SafetyConfig(BaseModel):
    policy_ref: Optional[str] = Field(default=None, description="OPA policy bundle or reference id")
    default_mode: Literal["mock", "emulated", "connected"] = Field(
        default="mock", description="Default sandbox/ops mode for the agent"
    )


class Provenance(BaseModel):
    created_by: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    builder_version: str = Field(default="v1")


class InstructionsPack(BaseModel):
    system: str = Field(..., description="System prompt")
    developer: Optional[str] = Field(default=None, description="Developer prompt")
    examples: Optional[List[Dict[str, Any]]] = Field(default=None)


class AgentBlueprintV1(BaseModel):
    adl_version: Literal["v1"] = Field(default="v1")
    agent_id: str = Field(...)
    role: str = Field(...)

    capabilities: Dict[str, int] = Field(default_factory=dict)
    tools: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    style: Optional[str] = Field(default=None)

    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    provenance: Provenance = Field(default_factory=Provenance)

    # References to related artifacts (persisted separately)
    instructions_ref: Optional[str] = Field(default=None)
    manifest_ref: Optional[str] = Field(default=None)

    notes: Optional[str] = Field(default=None)

