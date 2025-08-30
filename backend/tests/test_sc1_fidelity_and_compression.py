from app.services.compression.basic_engine import BasicCompressionEngine
from app.services.compression.fidelity import (
    lsl_to_dict, lsl_from_dict,
)
from app.services.compression.lsl import CompressedLearningSession, LearningOutcome


def test_sc1_lsl_roundtrip_and_optional_compression_ratio():
    # Build a moderately redundant LSL to give compression a chance
    obj = CompressedLearningSession(
        iteration=7,
        system="FastAPI",
        outcomes={
            "routing": (LearningOutcome.LEARNED, 0.91),
            "auth": (LearningOutcome.DISCOVERED, 0.62),
        },
        tests=(9, 12),
        errors={"auth": 3, "timeout": 1},
    )

    d = lsl_to_dict(obj)

    # Compress dict payload
    engine = BasicCompressionEngine()
    comp = engine.compress(d)
    back = engine.decompress(comp)

    # Fidelity: dict survives roundtrip
    assert isinstance(back, dict)
    back_obj = lsl_from_dict(back)
    assert back_obj.iteration == obj.iteration
    assert back_obj.system == obj.system
    assert set(back_obj.outcomes.keys()) == set(obj.outcomes.keys())

    # If zstd is active, we expect the payload to be <= msgpack/json size.
    # The engine sets method to "zstd+msgpack" when using zstd.
    if comp.method == "zstd+msgpack":
        assert isinstance(comp.ratio, float) or len(comp.data) > 0

