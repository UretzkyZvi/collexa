import json
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="function")
def client():
    return TestClient(app)


def test_a2a_signature_and_fields(client):
    agent_id = "agent-xyz"
    r = client.get(f"/v1/.well-known/a2a/{agent_id}.json")
    assert r.status_code == 200
    body = r.json()
    # Validate minimal fields
    assert body["id"] == agent_id
    assert body.get("issuer") == "collexa"
    assert body.get("alg") == "HS256"
    assert "signature" in body
    # Recompute signature
    import hmac
    import hashlib
    import os

    payload = {k: body[k] for k in body.keys() - {"alg", "signature"}}
    raw = json.dumps(payload, separators=(",", ":"))
    secret = os.getenv("APP_SIGNING_SECRET", "dev-secret").encode("utf-8")
    sig = hmac.new(secret, raw.encode("utf-8"), hashlib.sha256).hexdigest()
    assert sig == body["signature"]


def test_mcp_ws_list_and_call(client):
    with client.websocket_connect("/ws/mcp/agent-xyz") as ws:
        # list tools
        ws.send_text(json.dumps({"id": 1, "method": "tools/list"}))
        resp = json.loads(ws.receive_text())
        assert resp["id"] == 1
        assert isinstance(resp["result"], list)
        # call echo
        ws.send_text(
            json.dumps(
                {
                    "id": 2,
                    "method": "tools/call",
                    "params": {"tool": "invoke", "input": {"x": 1}},
                }
            )
        )
        resp2 = json.loads(ws.receive_text())
        assert resp2["id"] == 2
        assert resp2["result"]["tool"] == "invoke"
        assert resp2["result"]["echo"] == {"x": 1}
