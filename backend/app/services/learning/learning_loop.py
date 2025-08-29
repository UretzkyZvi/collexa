"""
N.2: Minimal autonomous learning loop (internal service).

This module provides a lightweight, dependency-free skeleton for a single
learning iteration that integrates SC.1 primitives:
- VectorRetriever for relevance
- HierarchicalContextManager for budgeted assembly
- LSL for compressed learning memory
- Optional MLflow metrics via tracking (safe no-op by default)
- Tooling registry for safe-by-default actions in mock/emulated modes

No new public endpoints. Intended for internal/dev usage and later upgrade to
Temporal or other workflow engines without changing core logic. Unit tests can
be added separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.services.compression.context_manager import HierarchicalContextManager, ContextLayer
from app.services.compression.vector_retrieval import VectorRetriever
from app.services.compression.lsl import CompressedLearningSession, LearningOutcome
from app.services.compression.adl import CompressedAgentBrief
from app.services.compression.opl import CompressedOptimizationTrace
from app.services.compression.tracking import run as tracking_run, log_metrics
from app.api.routers.learning import record_recent_learning
from app.services.learning.tools.registry import ToolRegistry


@dataclass
class IterationConfig:
    agent_id: str
    tasks: List[str]
    docs: List[str]
    total_budget_bytes: int = 20_000
    retriever_dim: int = 256
    retriever_top_k: int = 8
    system_label: str = "sandbox"
    sandbox_mode: str = "mock"  # mock|emulated|connected


def _seed_context(
    mgr: HierarchicalContextManager,
    agent_brief: Optional[CompressedAgentBrief],
    history: List[CompressedLearningSession],
    docs: List[str],
    examples: Optional[List[CompressedOptimizationTrace]] = None,
) -> None:
    # GLOBAL: agent brief
    if agent_brief:
        mgr.add_item("brief", ContextLayer.GLOBAL, agent_brief, fmt="adl", priority=10)
    # SESSION: recent learning sessions (most recent first)
    for i, sess in enumerate(reversed(history)):
        mgr.add_item(f"learn_{i}", ContextLayer.SESSION, sess, fmt="lsl", priority=5 - i)
    # DOMAIN/LOCAL: docs and local notes
    for j, d in enumerate(docs[:10]):
        mgr.add_item(f"doc_{j}", ContextLayer.DOMAIN, d, fmt="text", priority=3)
    # OPL examples (optional)
    if examples:
        for k, ex in enumerate(examples[:5]):
            mgr.add_item(f"opl_{k}", ContextLayer.GLOBAL, ex, fmt="opl", priority=4)


def _attempt_with_tools(task: str, assembled: Dict[str, Any], sandbox_mode: str) -> Tuple[bool, Dict[str, int], Dict[str, Any]]:
    """Attempt a task by selecting appropriate tools and invoking the best candidate.

    Minimal policy-aware selection:
    - Query the ToolRegistry for tools that can_handle(task)
    - Invoke the first candidate with a basic context inferred from task
    - Return success, errors, and a tool_usage meta to be tracked in LSL
    """
    registry = ToolRegistry()
    candidates = registry.select(task)
    if not candidates:
        return False, {"no_tool": 1}, {"used": None}

    tool = candidates[0]
    # Very naive context inference: if task mentions http/api, infer a GET to /
    ctx: Dict[str, Any] = {}
    tl = task.lower()
    if "http" in tl or "api" in tl or "rest" in tl:
        ctx = {"method": "GET", "url": "http://sandbox.local/"}
    elif any(x in tl for x in ("file", "fs", "write", "save")):
        ctx = {"action": "write", "path": "note.txt", "data": f"Task: {task}"}
    else:
        ctx = {"action": "read", "path": "note.txt"}

    res = tool.invoke(task, ctx, sandbox_mode=sandbox_mode)
    meta = {"used": getattr(tool, "spec", None).name if getattr(tool, "spec", None) else None, "mode": sandbox_mode}
    return res.success, (res.errors or {}), {**meta, "result_meta": (res.meta or {})}


def _derive_outcomes(task: str, success: bool) -> Dict[str, Tuple[LearningOutcome, float]]:
    concept = task.strip()[:24] or "task"
    if success:
        return {concept: (LearningOutcome.LEARNED, 0.8)}
    else:
        return {concept: (LearningOutcome.FAILED, 0.6)}


def run_learning_iteration(
    cfg: IterationConfig,
    agent_brief: Optional[CompressedAgentBrief] = None,
    history: Optional[List[CompressedLearningSession]] = None,
    examples: Optional[List[CompressedOptimizationTrace]] = None,
) -> CompressedLearningSession:
    """Execute a single learning iteration over the first task in cfg.tasks.

    - Seeds a HierarchicalContextManager with recent LSL, docs, brief, and OPL examples
    - Uses VectorRetriever to preselect by the task query and assembles within budgets
    - Selects and invokes a suitable tool (mock-safe) and derives outcomes/errors/tests
    - Records recent learning via record_recent_learning(), including tool usage metadata
    - Returns a CompressedLearningSession representing this iteration

    Safe by default: no external calls (mock), no new endpoints, optional tracking.
    """
    history = history or []
    task = (cfg.tasks[0] if cfg.tasks else "") or "general"

    mgr = HierarchicalContextManager(total_budget_bytes=cfg.total_budget_bytes)
    _seed_context(mgr, agent_brief=agent_brief, history=history, docs=cfg.docs, examples=examples)

    # Retrieval preselection
    vr = VectorRetriever(n_features=cfg.retriever_dim, use_faiss=False)
    mgr.preselect_with_retriever(task, retriever=vr, top_k=cfg.retriever_top_k)
    assembled = mgr.assemble()

    # Attempt via tools
    success, errors, tool_usage = _attempt_with_tools(task, assembled, sandbox_mode=cfg.sandbox_mode)
    outcomes = _derive_outcomes(task, success)
    tests = (1 if success else 0, 1)

    # Build session and record via dev helper
    iteration_num = (history[-1].iteration + 1) if history else 1
    session = CompressedLearningSession(
        iteration=iteration_num,
        system=cfg.system_label,
        outcomes=outcomes,
        tests=tests,
        errors=errors,
    )

    record_recent_learning(cfg.agent_id, {
        "iteration": session.iteration,
        "system": session.system,
        "outcomes": {k: {"code": v[0].value, "confidence": v[1]} for k, v in outcomes.items()},
        "tests": list(tests),
        "errors": errors,
        "tool": tool_usage,
    })

    # Optional metrics for the iteration
    try:
        with tracking_run("learning_iter", tags={"agent_id": cfg.agent_id}):
            log_metrics({
                "assembled_entries": float(len(assembled.get("entries", []))),
                "assembled_bytes": float(assembled.get("total_bytes", 0)),
                "success": 1.0 if success else 0.0,
            })
    except Exception:
        pass

    return session

