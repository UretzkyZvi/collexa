import os
import sys
import json
import pytest

# Skip if cryptography/python-jose are unavailable
pytest.importorskip("cryptography")
pytest.importorskip("jose")

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.security.jwks import derive_ec_p256_jwk_from_pem
from jose import jws
from jose.constants import ALGORITHMS


@pytest.mark.skip(reason="Integration test placeholder; enable in CI with proper keys")
def test_verify_signature_roundtrip(tmp_path, monkeypatch):
    # Generate a dev EC key (hard-coded minimal for test only)
    priv_pem = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIFj7NY1oH5xvQ9Z9v1bI8HqWvKY8tFf4oB7k7C8o3g+poAoGCCqGSM49
AwEHoUQDQgAEQ8Z9dNfY9b8O+2wYtH8Xq3a2r5f0u7vg6v1q8cX8VQ0v7f+f6cV6
0YcZlHnTGN0v0oO2z9Vf2k7nH7Sk2v4p3w==
-----END EC PRIVATE KEY-----"""
    monkeypatch.setenv("MANIFEST_PRIVATE_KEY_PEM", priv_pem)
    monkeypatch.setenv("MANIFEST_KEY_ID", "test-kid")

    manifest = {"agent_id": "a1", "version": "1.0", "capabilities": []}
    sig = jws.sign(
        payload=json.dumps(manifest),
        key=priv_pem,
        algorithm=ALGORITHMS.ES256,
        headers={"kid": "test-kid"},
    )
    assert sig

    jwk = derive_ec_p256_jwk_from_pem(private_pem=priv_pem, kid="test-kid")
    assert jwk
