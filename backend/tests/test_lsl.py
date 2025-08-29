from app.services.compression.lsl import CompressedLearningSession, LearningOutcome


def test_lsl_round_trip_simple():
    sess = CompressedLearningSession(
        iteration=47,
        system="FastAPI",
        outcomes={
            "routing": (LearningOutcome.LEARNED, 0.85),
            "Depends": (LearningOutcome.DISCOVERED, 0.87),
        },
        tests=(12, 12),
        errors={"auth": 3},
    )
    s = sess.to_lsl()
    back = CompressedLearningSession.from_lsl(s)

    assert back.iteration == 47
    assert back.system == "FastAPI"
    assert back.tests == (12, 12)
    assert back.errors.get("auth") == 3
    assert back.outcomes["routing"][0] == LearningOutcome.LEARNED
    assert abs(back.outcomes["routing"][1] - 0.85) < 1e-6


def test_lsl_parse_from_example_like_string():
    example = (
        "L47:FastAPI{"  # iteration and system
        "routing\u2192L:0.85,Depends\u2192D:0.87,"  # outcomes
        "T:12/12,auth:3}"  # tests + error
    )
    back = CompressedLearningSession.from_lsl(example)
    assert back.iteration == 47
    assert back.system == "FastAPI"
    assert back.tests == (12, 12)
    assert back.errors.get("auth") == 3
    assert back.outcomes["routing"][0] == LearningOutcome.LEARNED

