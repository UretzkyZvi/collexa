from app.services.compression.vector_retrieval import VectorRetriever


def test_vector_retriever_basic_query():
    vr = VectorRetriever(n_features=128, use_faiss=False)
    vr.add_item("k1", "FastAPI routing async dependencies", {"layer": "DOMAIN"})
    vr.add_item("k2", "React TypeScript frontend components", {"layer": "GLOBAL"})
    vr.add_item("k3", "DSPy optimization exemplars and heuristics", {"layer": "SESSION"})

    res = vr.query("frontend react components", top_k=2)
    # Should find k2 first
    assert res and res[0][0] == "k2"


def test_vector_retriever_filter_and_topk():
    vr = VectorRetriever(n_features=64, use_faiss=False)
    for i in range(20):
        vr.add_item(f"k{i}", f"item number {i}", {"mod": i % 2})

    res = vr.query("item number", top_k=5, filter_fn=lambda k, m: m.get("mod") == 1)
    assert len(res) <= 5
    assert all(m.get("mod") == 1 for (_, _, m) in res)

