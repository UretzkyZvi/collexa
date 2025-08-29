from app.services.compression.lsl import CompressedLearningSession, LearningOutcome
from app.services.compression.adl import CompressedAgentBrief
from app.services.compression.opl import CompressedOptimizationTrace
from app.services.compression.fidelity import (
    lsl_to_dict, lsl_from_dict,
    adl_to_dict, adl_from_dict,
    opl_to_dict, opl_from_dict,
)


def test_lsl_json_fidelity_round_trip():
    obj = CompressedLearningSession(
        iteration=12,
        system="FastAPI",
        outcomes={"routing": (LearningOutcome.LEARNED, 0.82)},
        tests=(8, 10),
        errors={"auth": 1},
    )
    d = lsl_to_dict(obj)
    back = lsl_from_dict(d)
    assert back.iteration == obj.iteration
    assert back.system == obj.system
    assert back.outcomes.keys() == obj.outcomes.keys()
    assert abs(back.outcomes["routing"][1] - 0.82) < 1e-6


def test_adl_json_fidelity_round_trip():
    obj = CompressedAgentBrief(
        agent_id="fs_dev",
        role="frontend",
        capabilities={"react": 5, "typescript": 5},
        tools=["gh", "slack"],
        constraints=["sec", "scale"],
        goals=["ship"],
        style="concise",
    )
    d = adl_to_dict(obj)
    back = adl_from_dict(d)
    assert back.agent_id == obj.agent_id
    assert back.capabilities == obj.capabilities
    assert back.tools == obj.tools


def test_opl_json_fidelity_round_trip():
    obj = CompressedOptimizationTrace(
        heuristics=["CoT", "SelfCheck"],
        metrics={"acc": "0.81"},
        exemplars=["ex1", "ex2"],
        params={"temp": "0.2"},
        notes="ok",
    )
    d = opl_to_dict(obj)
    back = opl_from_dict(d)
    assert back.heuristics == obj.heuristics
    assert back.metrics == obj.metrics
    assert back.params == obj.params

