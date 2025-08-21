from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Any, Dict
import os
import json

try:
    from jose import jws
    from jose.constants import ALGORITHMS
except Exception:  # pragma: no cover
    jws = None
    ALGORITHMS = type("ALG", (), {"ES256": "ES256"})

from app.api.deps import require_team
from app.db.session import get_db
from app.db import models

router = APIRouter()


def _load_jwks() -> Dict[str, Any]:
    """Load JWKS from env variables, deriving from PEM if needed."""
    from app.security.jwks import derive_jwks_from_env

    # Construct an env dict explicitly to allow test injection
    env = {k: v for k, v in os.environ.items() if k.startswith("MANIFEST_")}
    return derive_jwks_from_env(env)


@router.post("/agents/{agent_id}/manifests")
async def create_agent_manifest(
    agent_id: str,
    auth=Depends(require_team),
    db: Session = Depends(get_db),
):
    row = (
        db.query(models.Agent)
        .filter(models.Agent.id == agent_id, models.Agent.org_id == auth.get("org_id"))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Construct a minimal manifest; extend as capabilities grow
    manifest = {
        "agent_id": agent_id,
        "version": "1.0",
        "issuer": "collexa",
        "capabilities": [],
    }

    key_id = os.getenv("MANIFEST_KEY_ID", "dev-key")
    priv_pem = os.getenv("MANIFEST_PRIVATE_KEY_PEM")

    if not jws or not priv_pem:
        # Allow running without crypto libs/keys in dev; return unsigned manifest
        result = {
            "manifest": manifest,
            "signature": None,
            "key_id": key_id,
            "alg": None,
        }
    else:
        headers = {"alg": "ES256", "kid": key_id, "typ": "JWT"}
        try:
            signature = jws.sign(
                payload=json.dumps(manifest, separators=(",", ":")),
                key=priv_pem,
                algorithm=ALGORITHMS.ES256,
                headers=headers,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Signing failed: {e}")

        result = {
            "manifest": manifest,
            "signature": signature,
            "key_id": key_id,
            "alg": "ES256",
        }

    # Persist (best-effort; table may not exist yet in dev)
    try:
        db.add(
            models.A2AManifest(
                id=f"{agent_id}:{key_id}",
                agent_id=agent_id,
                version=manifest["version"],
                manifest_json=manifest,
                signature=result.get("signature"),
                key_id=key_id,
            )
        )
        db.commit()
    except Exception:
        # If migrations not applied yet, skip persistence in dev.
        db.rollback()

    return result


@router.get("/.well-known/jwks.json")
async def get_jwks():
    jwks = _load_jwks()
    if not jwks:
        # Return empty set to avoid leaking dev keys; clients should handle absence.
        return {"keys": []}
    return jwks


@router.post("/agents/{agent_id}/manifests/verify")
async def verify_agent_manifest(
    agent_id: str,
    payload: Dict[str, Any],
):
    """Verify a signed manifest token using current JWKS.

    Body: {"signature": "<jws>", "expect": {optional fields to compare}}
    """
    token = payload.get("signature")
    if not token:
        raise HTTPException(status_code=400, detail="signature is required")

    jwks = _load_jwks()
    keys = jwks.get("keys", []) if isinstance(jwks, dict) else []
    if not keys:
        raise HTTPException(status_code=503, detail="No verifier keys available")

    # Attempt verification against any key in the JWKS
    last_err = None
    for k in keys:
        try:
            # Reconstruct PEM from JWK and verify
            from app.security.jwks import ec_p256_jwk_to_public_pem
            from jose import jws as _jws
            from jose.constants import ALGORITHMS as _ALG

            pem = ec_p256_jwk_to_public_pem(k)
            if not pem:
                continue
            payload_json = _jws.verify(token, pem, algorithms=[_ALG.ES256])
            # Optionally validate expected fields
            exp = payload.get("expect") or {}
            if exp:
                import json as _json

                data = _json.loads(payload_json)
                for field, value in exp.items():
                    if data.get(field) != value:
                        raise HTTPException(
                            status_code=400, detail=f"Mismatch on field '{field}'"
                        )
            return {"valid": True}
        except Exception as e:  # try next key
            last_err = str(e)
            continue

    raise HTTPException(status_code=400, detail=f"Invalid signature: {last_err}")
