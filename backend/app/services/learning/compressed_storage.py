"""
N.2 integration stub for learning session storage using LSL (SC.1-02).

This provides a minimal interface to compress/decompress learning sessions for
storage using the Learning State Language and the shared compression engine.

For now, this module focuses on in-memory conversion to/from LSL strings, which
can be persisted to JSON/Text fields. A future iteration can add DB models as
needed.
"""
from __future__ import annotations
from typing import Dict, Tuple

from app.services.compression.lsl import CompressedLearningSession, LearningOutcome


class CompressedLearningMemory:
    """Simple in-memory helper to serialize learning sessions as LSL strings.

    This can be replaced or extended with a DB-backed implementation.
    """

    def __init__(self):
        self._store: Dict[str, str] = {}  # key -> LSL string

    def store_session(
        self,
        key: str,
        iteration: int,
        system: str,
        outcomes: Dict[str, Tuple[LearningOutcome, float]],
        tests: Tuple[int, int],
        errors: Dict[str, int],
    ) -> str:
        sess = CompressedLearningSession(
            iteration=iteration,
            system=system,
            outcomes=outcomes,
            tests=tests,
            errors=errors,
        )
        lsl = sess.to_lsl()
        self._store[key] = lsl
        return lsl

    def load_session(self, key: str) -> CompressedLearningSession | None:
        s = self._store.get(key)
        if not s:
            return None
        try:
            return CompressedLearningSession.from_lsl(s)
        except Exception:
            return None

