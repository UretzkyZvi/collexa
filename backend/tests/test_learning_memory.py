from app.services.learning.compressed_storage import CompressedLearningMemory
from app.services.compression.lsl import LearningOutcome


def test_in_memory_learning_storage_roundtrip():
    mem = CompressedLearningMemory()

    key = "agentA-fastapi-iter47"
    lsl = mem.store_session(
        key=key,
        iteration=47,
        system="FastAPI",
        outcomes={
            "routing": (LearningOutcome.LEARNED, 0.85),
            "Depends": (LearningOutcome.DISCOVERED, 0.87),
        },
        tests=(12, 12),
        errors={"auth": 3},
    )

    assert lsl.startswith("L47:FastAPI{")

    sess = mem.load_session(key)
    assert sess is not None
    assert sess.iteration == 47
    assert sess.system == "FastAPI"
    assert sess.tests == (12, 12)
    assert sess.errors.get("auth") == 3
    assert sess.outcomes["routing"][0] == LearningOutcome.LEARNED

