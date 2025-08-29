from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel, Field

from app.api.deps import require_team
from app.services.learning.compressed_storage import CompressedLearningMemory

router = APIRouter()
_memory = CompressedLearningMemory()


@router.get("/dev/learning/{agent_id}/recent")
async def get_recent_learning(agent_id: str):
    # Dev-only: return a single recent entry if present (in-memory)
    key = f"{agent_id}-recent"
    session = _memory.load_session(key)
    if not session:
        raise HTTPException(status_code=404, detail="No recent learning session")
    return {
        "agent_id": agent_id,
        "lsl": session.to_lsl(),
        "iteration": session.iteration,
        "system": session.system,
        "tests": {"passed": session.tests[0], "total": session.tests[1]},
        "errors": session.errors,
        "outcomes": {k: {"code": v[0].value, "confidence": v[1]} for k, v in session.outcomes.items()},
    }


class Outcome(BaseModel):
    code: str = Field(pattern=r"^[LDMFR]$")
    confidence: float


class LearningSessionBody(BaseModel):
    iteration: int
    system: str
    outcomes: dict[str, Outcome]
    tests: tuple[int, int] | list[int]
    errors: dict[str, int] | None = None


def record_recent_learning(agent_id: str, session: dict):
    """Helper for learning loops to record a recent session in-memory.

    The session dict should include: iteration (int), system (str), outcomes (mapping),
    tests (passed,total), errors mapping.
    Outcomes must map concept -> {"code": "L|D|M|F|R", "confidence": float}.
    """
    from app.services.compression.lsl import LearningOutcome

    outcomes = {
        concept: (LearningOutcome(v.get("code")), float(v.get("confidence", 0.0)))
        for concept, v in (session.get("outcomes") or {}).items()
    }
    tests = tuple(session.get("tests") or (0, 0))  # type: ignore[assignment]
    errors = session.get("errors") or {}

    _memory.store_session(
        key=f"{agent_id}-recent",
        iteration=int(session.get("iteration", 0)),
        system=str(session.get("system", "unknown")),
        outcomes=outcomes,
        tests=tests,  # type: ignore[arg-type]
        errors=errors,
    )


@router.post("/dev/learning/{agent_id}/recent")
async def post_recent_learning(agent_id: str, body: LearningSessionBody):
    # Accept a raw session dict (dev-only) and record it in-memory via record_recent_learning
    record_recent_learning(agent_id, body.model_dump())
    return {"status": "ok"}




class LearningIterationBody(BaseModel):
    tasks: list[str]
    docs: list[str] = []
    retriever_top_k: int | None = None
    total_budget_bytes: int | None = None
    system: str | None = None
    sandbox_mode: str | None = None  # mock|emulated|connected


@router.post("/dev/learning/{agent_id}/iterate")
async def iterate_learning(agent_id: str, body: LearningIterationBody):
    """Dev-only: trigger a minimal learning iteration and record recent LSL.

    This wires N.2 to SC.1 primitives without external dependencies. It uses
    VectorRetriever + HierarchicalContextManager to assemble a context for the
    first task, performs a stubbed attempt and error analysis, invokes a mock-safe
    tool, and records the resulting LSL via record_recent_learning().
    """
    from app.services.learning.learning_loop import run_learning_iteration, IterationConfig

    # Load last session (if any) as a one-item history buffer
    prior = _memory.load_session(f"{agent_id}-recent")
    history = [prior] if prior else []

    cfg = IterationConfig(
        agent_id=agent_id,
        tasks=body.tasks,
        docs=body.docs,
        total_budget_bytes=body.total_budget_bytes or 20_000,
        retriever_top_k=body.retriever_top_k or 8,
        system_label=body.system or "sandbox",
        sandbox_mode=body.sandbox_mode or "mock",
    )

    session = run_learning_iteration(cfg, agent_brief=None, history=history, examples=None)

    return {
        "status": "ok",
        "agent_id": agent_id,
        "iteration": session.iteration,
        "lsl": session.to_lsl(),
        "system": session.system,
        "tests": {"passed": session.tests[0], "total": session.tests[1]},
        "errors": session.errors,
        "outcomes": {k: {"code": v[0].value, "confidence": v[1]} for k, v in session.outcomes.items()},
    }
