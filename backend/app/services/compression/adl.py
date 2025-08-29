"""
SC.1-03: Agent Definition Language (ADL)

Compact representation of an agent brief for transport/storage.
Initial minimal schema with round-trip parsing:
- A: <agent_id>
- R: <role>
- C: <capabilities as name:level,...>  level in 1..5
- T: <tools as name1,name2,...>
- X: <constraints short-codes or phrases>
- G: <goals/objectives>
- S: <style/guidelines>

Example:
A:fs_dev|R:frontend|C:react:5,typescript:5,node:5|T:github,slack|X:security,scale|G:ship features fast|S:concise

Notes:
- All sections are optional except A (agent_id)
- Order is preserved for deterministic output
- Values are kept short; commas and pipes are reserved by design
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re


@dataclass
class CompressedAgentBrief:
    agent_id: str
    role: Optional[str] = None
    capabilities: Dict[str, int] = field(default_factory=dict)  # name -> 1..5
    tools: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    style: Optional[str] = None

    def to_adl(self) -> str:
        parts: List[str] = [f"A:{_escape(self.agent_id)}"]
        if self.role:
            parts.append(f"R:{_escape(self.role)}")
        if self.capabilities:
            # deterministic ordering by key
            caps = ",".join(f"{_escape(k)}:{int(v)}" for k, v in sorted(self.capabilities.items()))
            parts.append(f"C:{caps}")
        if self.tools:
            tools = ",".join(_escape(t) for t in self.tools)
            parts.append(f"T:{tools}")
        if self.constraints:
            xs = ",".join(_escape(x) for x in self.constraints)
            parts.append(f"X:{xs}")
        if self.goals:
            gs = ",".join(_escape(g) for g in self.goals)
            parts.append(f"G:{gs}")
        if self.style:
            parts.append(f"S:{_escape(self.style)}")
        return "|".join(parts)

    @classmethod
    def from_adl(cls, s: str) -> "CompressedAgentBrief":
        # Split by unescaped pipes into sections like K:...
        if not s or "A:" not in s:
            raise ValueError("ADL must include A:<agent_id>")
        sections = _split_escaped(s, "|")
        data: Dict[str, str] = {}
        for sec in sections:
            if not sec:
                continue
            idx = _find_unescaped(sec, ":")
            if idx == -1:
                continue
            k = sec[:idx]
            v = sec[idx + 1 :]
            data[k] = v

        agent_id = _unescape(data.get("A", "").strip())
        if not agent_id:
            raise ValueError("Missing agent_id (A)")

        role = _unescape(data.get("R", "").strip()) or None

        capabilities: Dict[str, int] = {}
        if "C" in data and data["C"]:
            for item in _split_escaped(data["C"], ","):
                if not item:
                    continue
                idx = _find_unescaped(item, ":")
                if idx == -1:
                    continue
                name = _unescape(item[:idx])
                level = item[idx + 1 :]
                try:
                    lvl = int(level)
                except Exception:
                    continue
                capabilities[name] = max(1, min(5, lvl))

        tools: List[str] = []
        if "T" in data and data["T"]:
            tools = [_unescape(t) for t in _split_escaped(data["T"], ",") if t]

        constraints: List[str] = []
        if "X" in data and data["X"]:
            constraints = [_unescape(x) for x in _split_escaped(data["X"], ",") if x]

        goals: List[str] = []
        if "G" in data and data["G"]:
            goals = [_unescape(g) for g in _split_escaped(data["G"], ",") if g]

        style = _unescape(data.get("S", "").strip()) or None

        return cls(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities,
            tools=tools,
            constraints=constraints,
            goals=goals,
            style=style,
        )


def _escape(text: str) -> str:
    # Basic escaping for reserved delimiters: | , : and backslash
    return (
        text.replace("\\", "\\\\")
        .replace("|", r"\|")
        .replace(",", r"\,")
        .replace(":", r"\:")
    )


def _unescape(text: str) -> str:
    # Reverse escaping: interpret backslash as escaping the next char
    out = []
    it = iter(range(len(text)))
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            out.append(text[i + 1])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _find_unescaped(s: str, ch: str) -> int:
    i = 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == ch:
            return i
        i += 1
    return -1


def _split_escaped(s: str, sep: str, preserve_escape: bool = True) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            if preserve_escape:
                buf.append("\\")
            buf.append(s[i + 1])
            i += 2
            continue
        if c == sep:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts

