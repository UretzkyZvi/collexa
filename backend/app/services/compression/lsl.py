"""
SC.1-02: Learning State Language (LSL)

Minimal, testable encoder/decoder for compressed learning sessions, aligned with
our docs. This is an initial version to unblock integration; it focuses on
round-trip fidelity for core fields.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple
import re


class LearningOutcome(Enum):
    LEARNED = "L"
    DISCOVERED = "D"
    MASTERED = "M"
    FAILED = "F"
    REVIEWED = "R"


@dataclass
class CompressedLearningSession:
    iteration: int
    system: str
    outcomes: Dict[str, Tuple[LearningOutcome, float]]  # concept -> (code, conf)
    tests: Tuple[int, int]  # passed, total
    errors: Dict[str, int]

    def to_lsl(self) -> str:
        parts = []
        # outcomes
        if self.outcomes:
            outcomes_str = ",".join(
                f"{concept}\u2192{code.value}:{confidence:.2f}"
                for concept, (code, confidence) in self.outcomes.items()
            )
            parts.append(outcomes_str)
        # tests
        if self.tests and self.tests[1] > 0:
            parts.append(f"T:{self.tests[0]}/{self.tests[1]}")
        # errors
        if self.errors:
            parts.append(",".join(f"{k}:{v}" for k, v in self.errors.items()))

        inner = ",".join(parts)
        return f"L{self.iteration}:{self.system}{{{inner}}}"

    @classmethod
    def from_lsl(cls, s: str) -> "CompressedLearningSession":
        # L47:FastAPI{routing→L:0.85,Depends→D:0.87,T:8/10,E:auth:3}
        m = re.match(r"^L(\d+):([^\{]+)\{(.*)\}$", s)
        if not m:
            raise ValueError("Invalid LSL string")
        iteration = int(m.group(1))
        system = m.group(2)
        body = m.group(3)

        outcomes: Dict[str, Tuple[LearningOutcome, float]] = {}
        tests = (0, 0)
        errors: Dict[str, int] = {}

        # Split by commas but keep key patterns
        tokens = [t for t in body.split(",") if t]
        for tok in tokens:
            if tok.startswith("T:"):
                # T:8/10
                try:
                    nums = tok.split(":", 1)[1]
                    p, t = nums.split("/")
                    tests = (int(p), int(t))
                except Exception:
                    continue
            elif ":" in tok and "\u2192" in tok:
                # concept→X:0.99
                try:
                    left, conf_str = tok.split(":", 1)
                    concept, code = left.split("\u2192", 1)
                    code_enum = LearningOutcome(code)
                    outcomes[concept] = (code_enum, float(conf_str))
                except Exception:
                    continue
            elif ":" in tok:
                # error pattern like auth:3
                try:
                    k, v = tok.split(":", 1)
                    errors[k] = int(v)
                except Exception:
                    continue

        return cls(iteration=iteration, system=system, outcomes=outcomes, tests=tests, errors=errors)

