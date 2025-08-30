from app.services.capability_naming import capability_key, normalize_action


def test_capability_key_normalization():
    assert capability_key("HTTP", "GET") == "tool:http:get"
    assert capability_key("fs", " read ") == "tool:fs:read"
    assert capability_key("graphql", "Query") == "tool:graphql:query"
    assert capability_key("ws", "connect/") == "tool:ws:connect"


def test_normalize_action_passthrough():
    assert normalize_action("custom") == "custom"

