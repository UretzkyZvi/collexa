from fastapi.testclient import TestClient
from app.main import app
from app.services.manifest_signing import sign_manifest_if_possible
from app.security.jwks import derive_jwks_from_env, ec_p256_jwk_to_public_pem


import pytest

def _gen_ec_p256_private_pem():
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
    except Exception:
        pytest.skip("cryptography is unavailable; skipping signing generation test")
        return ""

    priv = ec.generate_private_key(ec.SECP256R1())
    pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return pem


def _mock_auth(monkeypatch):
    from app.security import stack_auth

    monkeypatch.setattr(
        stack_auth,
        "verify_stack_access_token",
        lambda t: {"id": "u1", "selectedTeamId": "o1"},
    )
    monkeypatch.setattr(stack_auth, "verify_team_membership", lambda team, tok: {"id": team})


def test_manifest_signing_helper_unit(monkeypatch):
    pem = _gen_ec_p256_private_pem()
    if not pem:
        return
    monkeypatch.setenv("MANIFEST_PRIVATE_KEY_PEM", pem)
    monkeypatch.setenv("MANIFEST_KEY_ID", "unit-test-key")

    manifest = {"agent_id": "a1", "version": "1.0"}
    result = sign_manifest_if_possible(manifest)

    assert result["manifest"]["agent_id"] == "a1"
    assert result["key_id"] == "unit-test-key"
    assert result["alg"] in ("ES256", None)

    # Verify signature with derived JWKS if present
    if result["signature"]:
        jwks = derive_jwks_from_env({
            "MANIFEST_PRIVATE_KEY_PEM": pem,
            "MANIFEST_KEY_ID": "unit-test-key",
        })
        pub_pem = ec_p256_jwk_to_public_pem(jwks["keys"][0])
        assert pub_pem
        from jose import jws as _jws
        from jose.constants import ALGORITHMS as _ALG

        payload_json = _jws.verify(result["signature"], pub_pem, algorithms=[_ALG.ES256])
        assert '"agent_id":"a1"' in payload_json


def test_manifest_verify_endpoint_integration(monkeypatch):
    client = TestClient(app)
    pem = _gen_ec_p256_private_pem()
    if not pem:
        return
    monkeypatch.setenv("MANIFEST_PRIVATE_KEY_PEM", pem)
    monkeypatch.setenv("MANIFEST_KEY_ID", "it-key")

    _mock_auth(monkeypatch)

    # Create agent via builder and get signed manifest
    resp = client.post(
        "/v1/agents/builder/create",
        json={"brief": "ux designer"},
        headers={"Authorization": "Bearer t", "X-Team-Id": "o1"},
    )
    assert resp.status_code == 200
    data = resp.json()

    signature = data.get("manifest", {}).get("signature") or data.get("signature")
    agent_id = data["agent_id"]

    # Verify via endpoint using JWKS derived from env
    r2 = client.post(
        f"/v1/agents/{agent_id}/manifests/verify",
        json={"signature": signature, "expect": {"agent_id": agent_id}},
    )
    assert r2.status_code == 200
    assert r2.json()["valid"] is True

