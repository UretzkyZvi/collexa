from app.schemas.agent_blueprint import AgentBlueprintV1, InstructionsPack


def test_adl_v1_schema_defaults_and_fields():
    bp = AgentBlueprintV1(agent_id="a1", role="ux_designer")
    assert bp.adl_version == "v1"
    assert bp.agent_id == "a1"
    assert bp.role == "ux_designer"
    # Defaults
    assert bp.capabilities == {}
    assert bp.tools == []
    assert bp.constraints == []
    assert bp.goals == []
    assert bp.safety.default_mode == "mock"
    assert bp.provenance.builder_version == "v1"


def test_instructions_pack_model():
    instr = InstructionsPack(system="You are a UX designer...", developer="Use tools wisely")
    assert instr.system.startswith("You are")

