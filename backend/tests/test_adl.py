from app.services.compression.adl import CompressedAgentBrief


def test_adl_round_trip():
    brief = CompressedAgentBrief(
        agent_id="fs_dev",
        role="frontend",
        capabilities={"react": 5, "typescript": 5, "node": 5},
        tools=["github", "slack"],
        constraints=["security", "scale"],
        goals=["ship features fast"],
        style="concise",
    )
    s = brief.to_adl()
    parsed = CompressedAgentBrief.from_adl(s)

    assert parsed.agent_id == "fs_dev"
    assert parsed.role == "frontend"
    assert parsed.capabilities["react"] == 5
    assert "github" in parsed.tools
    assert "security" in parsed.constraints
    assert parsed.goals[0].startswith("ship features")
    assert parsed.style == "concise"


def test_adl_parsing_and_escaping():
    s = (
        r"A:agent\|id|R:front\:end|C:react\:dom:5,ts\,node:4|T:gh\,hub,sl\|ack|"
        r"X:sec\,urity|G:deliver\:fast|S:con\|cise"
    )
    parsed = CompressedAgentBrief.from_adl(s)

    assert parsed.agent_id == "agent|id"
    assert parsed.role == "front:end"
    assert parsed.capabilities.get("react:dom") == 5
    assert parsed.capabilities.get("ts,node") == 4
    assert parsed.tools[0] == "gh,hub"
    assert parsed.tools[1] == "sl|ack"
    assert parsed.constraints[0] == "sec,urity"
    assert parsed.goals[0] == "deliver:fast"
    assert parsed.style == "con|cise"

    # Round-trip keeps escaping intact
    out = parsed.to_adl()
    parsed2 = CompressedAgentBrief.from_adl(out)
    assert parsed2.agent_id == parsed.agent_id
    assert parsed2.tools == parsed.tools

