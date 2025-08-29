from app.services.compression.context_manager import HierarchicalContextManager, ContextLayer
from app.services.compression.vector_retrieval import VectorRetriever
from app.services.compression.lsl import CompressedLearningSession, LearningOutcome
from app.services.compression.adl import CompressedAgentBrief


def test_preselect_with_retriever_limits_items():
    mgr = HierarchicalContextManager(total_budget_bytes=5000)
    # Add 4 items across layers
    adl = CompressedAgentBrief(agent_id="fs_dev", role="frontend", capabilities={"react": 5}, tools=["github"], constraints=[], goals=["ship"], style=None)
    mgr.add_item("brief", ContextLayer.GLOBAL, adl, fmt="adl", priority=10)

    lsl = CompressedLearningSession(iteration=1, system="FastAPI", outcomes={"routing": (LearningOutcome.LEARNED, 0.8)}, tests=(8, 10), errors={})
    mgr.add_item("learn", ContextLayer.SESSION, lsl, fmt="lsl", priority=5)

    mgr.add_item("domain_notes", ContextLayer.DOMAIN, {"text": "payment provider integration and billing"}, fmt="json", priority=3)
    mgr.add_item("local_dbg", ContextLayer.LOCAL, "debug trace for sandbox", fmt="text", priority=1)

    vr = VectorRetriever(n_features=128, use_faiss=False)
    # Preselect items relevant to frontend/react query
    mgr.preselect_with_retriever("react frontend", retriever=vr, top_k=2)

    res = mgr.assemble()
    keys = [e["key"] for e in res["entries"]]
    # Expect only items most relevant to "react frontend" (likely brief)
    assert "brief" in keys and len(keys) <= 2

