from __future__ import annotations

from typing import Dict, Any, Optional
import os
import json

try:
    from jose import jws
    from jose.constants import ALGORITHMS
except Exception:  # pragma: no cover
    jws = None
    ALGORITHMS = type("ALG", (), {"ES256": "ES256"})

from app.security.jwks import derive_jwks_from_env


def sign_manifest_if_possible(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Sign manifest using ES256 if MANIFEST_PRIVATE_KEY_PEM is present.

    Returns dict: {"manifest", "signature", "key_id", "alg"}
    If signing is not possible, signature is None and alg is None.
    """
    env = {k: v for k, v in os.environ.items() if k.startswith("MANIFEST_")}
    key_id = env.get("MANIFEST_KEY_ID") or "dev-key"
    priv_pem = env.get("MANIFEST_PRIVATE_KEY_PEM")

    if not jws or not priv_pem:
        return {"manifest": manifest, "signature": None, "key_id": key_id, "alg": None}

    try:
        signature = jws.sign(
            payload=json.dumps(manifest, separators=(",", ":")),
            key=priv_pem,
            algorithm=ALGORITHMS.ES256,
            headers={"alg": "ES256", "kid": key_id, "typ": "JWT"},
        )
        return {"manifest": manifest, "signature": signature, "key_id": key_id, "alg": "ES256"}
    except Exception:
        # Fail safe: return unsigned if signing fails
        return {"manifest": manifest, "signature": None, "key_id": key_id, "alg": None}

