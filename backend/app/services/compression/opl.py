"""
SC.1-04: Optimization Pattern Language (OPL)

Compact representation of optimization runs / traces.
Initial minimal schema with round-trip parsing and escaping-aware delimiters.

Format (pipe-separated sections):
- H: heuristic(s) applied (comma separated)
- M: metrics key:val pairs (comma separated)
- E: exemplar IDs or tags (comma separated)
- P: parameters key:val pairs (comma separated)
- N: notes/summary (free text)

Example:
H:CoT+SelfCheck|M:acc:0.82,lat:95ms,cost:0.12|E:ex#12,ex#48|P:temp:0.2,top_p:0.9|N:improved on auth cases
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .adl import _escape, _unescape, _find_unescaped, _split_escaped


@dataclass
class CompressedOptimizationTrace:
    heuristics: List[str] = field(default_factory=list)
    metrics: Dict[str, str] = field(default_factory=dict)
    exemplars: List[str] = field(default_factory=list)
    params: Dict[str, str] = field(default_factory=dict)
    notes: Optional[str] = None

    def to_opl(self) -> str:
        parts: List[str] = []
        if self.heuristics:
            parts.append("H:" + ",".join(_escape(h) for h in self.heuristics))
        if self.metrics:
            parts.append("M:" + ",".join(f"{_escape(k)}:{_escape(str(v))}" for k, v in self.metrics.items()))
        if self.exemplars:
            parts.append("E:" + ",".join(_escape(e) for e in self.exemplars))
        if self.params:
            parts.append("P:" + ",".join(f"{_escape(k)}:{_escape(str(v))}" for k, v in self.params.items()))
        if self.notes:
            parts.append("N:" + _escape(self.notes))
        return "|".join(parts)

    @classmethod
    def from_opl(cls, s: str) -> "CompressedOptimizationTrace":
        data: Dict[str, str] = {}
        for sec in _split_escaped(s, "|"):
            if not sec:
                continue
            idx = _find_unescaped(sec, ":")
            if idx == -1:
                continue
            k = sec[:idx]
            v = sec[idx + 1 :]
            data[k] = v

        heuristics: List[str] = []
        if "H" in data and data["H"]:
            heuristics = [_unescape(h) for h in _split_escaped(data["H"], ",") if h]

        metrics: Dict[str, str] = {}
        if "M" in data and data["M"]:
            for item in _split_escaped(data["M"], ","):
                if not item:
                    continue
                idx = _find_unescaped(item, ":")
                if idx == -1:
                    continue
                k = _unescape(item[:idx])
                v = _unescape(item[idx + 1 :])
                metrics[k] = v

        exemplars: List[str] = []
        if "E" in data and data["E"]:
            exemplars = [_unescape(e) for e in _split_escaped(data["E"], ",") if e]

        params: Dict[str, str] = {}
        if "P" in data and data["P"]:
            for item in _split_escaped(data["P"], ","):
                if not item:
                    continue
                idx = _find_unescaped(item, ":")
                if idx == -1:
                    continue
                k = _unescape(item[:idx])
                v = _unescape(item[idx + 1 :])
                params[k] = v

        notes: Optional[str] = None
        if "N" in data and data["N"]:
            notes = _unescape(data["N"]) or None

        return cls(
            heuristics=heuristics,
            metrics=metrics,
            exemplars=exemplars,
            params=params,
            notes=notes,
        )

