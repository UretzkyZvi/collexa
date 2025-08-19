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


@router.post("/agents/{agent_id}/manifests")
async def create_agent_manifest(
    agent_id: str,
    payload: Dict[str, Any] | None = None,
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
        result = {"manifest": manifest, "signature": None, "key_id": key_id, "alg": None}
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

        result = {"manifest": manifest, "signature": signature, "key_id": key_id, "alg": "ES256"}

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

