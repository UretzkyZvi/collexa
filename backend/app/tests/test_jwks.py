import os
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

pytest.importorskip("cryptography")

from app.security.jwks import derive_ec_p256_jwk_from_pem, derive_jwks_from_env


def test_derive_jwk_from_invalid_pem_returns_none():
    jwk = derive_ec_p256_jwk_from_pem(private_pem="not-a-key")
    assert jwk is None


def test_derive_jwks_from_env_prefers_json(monkeypatch):
    monkeypatch.setenv(
        "MANIFEST_JWKS_JSON", '{"keys":[{"kty":"EC","crv":"P-256","x":"AA","y":"BB"}]}'
    )
    jwks = derive_jwks_from_env(dict(os.environ))
    assert jwks.get("keys")


def test_derive_jwks_from_env_empty_without_keys(monkeypatch):
    monkeypatch.delenv("MANIFEST_JWKS_JSON", raising=False)
    monkeypatch.delenv("MANIFEST_PUBLIC_KEY_PEM", raising=False)
    monkeypatch.delenv("MANIFEST_PRIVATE_KEY_PEM", raising=False)
    jwks = derive_jwks_from_env(dict(os.environ))
    assert jwks == {"keys": []}
