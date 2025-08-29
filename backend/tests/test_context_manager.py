from app.services.compression.context_manager import HierarchicalContextManager, ContextLayer
from app.services.compression.lsl import CompressedLearningSession, LearningOutcome
from app.services.compression.adl import CompressedAgentBrief
from app.services.compression.opl import CompressedOptimizationTrace


def test_context_manager_budget_allocation():
    mgr = HierarchicalContextManager(total_budget_bytes=2000)

    # Global ADL
    adl = CompressedAgentBrief(
        agent_id="fs_dev",
        role="frontend",
        capabilities={"react": 5, "typescript": 5, "node": 5},
        tools=["github", "slack"],
        constraints=["security", "scale"],
        goals=["ship fast"],
        style="concise",
    )
    mgr.add_item("agent_brief", ContextLayer.GLOBAL, adl, fmt="adl", priority=10)

    # Domain OPL
    opl = CompressedOptimizationTrace(
        heuristics=["CoT", "SelfCheck"],
        metrics={"acc": "0.82", "lat": "95ms"},
        exemplars=["ex#12", "ex#48"],
        params={"temp": "0.2"},
        notes="auth focus",
    )
    mgr.add_item("domain_optim", ContextLayer.DOMAIN, opl, fmt="opl", priority=8)

    # Session LSL
    lsl = CompressedLearningSession(
        iteration=47,
        system="FastAPI",
        outcomes={
            "routing": (LearningOutcome.LEARNED, 0.85),
            "Depends": (LearningOutcome.DISCOVERED, 0.87),
        },
        tests=(12, 12),
        errors={"auth": 3},
    )
    mgr.add_item("session_learn", ContextLayer.SESSION, lsl, fmt="lsl", priority=5)

    # Local text (large to force cutoff)
    big_local = {"notes": "x" * 5000}
    mgr.add_item("local_notes", ContextLayer.LOCAL, big_local, fmt="json", priority=1)

    result = mgr.assemble()
    assert result["total_bytes"] > 0
    keys = [e["key"] for e in result["entries"]]
    assert "agent_brief" in keys and "domain_optim" in keys and "session_learn" in keys
    assert "local_notes" not in keys  # should be dropped due to layer/total budget


def test_context_manager_respects_layer_budgets():
    # Tight budgets to verify exclusion order
    mgr = HierarchicalContextManager(total_budget_bytes=600, per_layer_budget={
        ContextLayer.GLOBAL: 200,
        ContextLayer.DOMAIN: 200,
        ContextLayer.SESSION: 200,
        ContextLayer.LOCAL: 100,
    })

    # Add multiple locals; only some should fit
    for i in range(5):
        mgr.add_item(f"local_{i}", ContextLayer.LOCAL, {"n": "y" * 50}, fmt="json", priority=i)

    res = mgr.assemble()
    local_entries = [e for e in res["entries"] if e["layer"] == "LOCAL"]
    assert len(local_entries) >= 1
    # Ensure none exceeds per-layer budget in sum
    assert sum(e["size"] for e in local_entries) <= 100

