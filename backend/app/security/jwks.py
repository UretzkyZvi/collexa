import base64
from typing import Optional, Dict, Any


def _b64url_nopad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def derive_ec_p256_jwk_from_pem(
    *, private_pem: Optional[str] = None, public_pem: Optional[str] = None, kid: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Derive an EC P-256 JWK from PEM input. Returns None if not derivable.

    Accepts either a private key PEM (preferred) or a public key PEM.
    """
    pub_key = None

    if private_pem:
        try:
            from cryptography.hazmat.primitives.asymmetric import ec as _ec
            from cryptography.hazmat.primitives.serialization import load_pem_private_key as _load_priv

            priv = _load_priv(private_pem.encode("utf-8"), password=None)
            if not isinstance(priv, _ec.EllipticCurvePrivateKey):
                return None
            if not isinstance(priv.curve, _ec.SECP256R1):
                return None
            pub_key = priv.public_key()
        except Exception:
            return None
    elif public_pem:
        try:
            from cryptography.hazmat.primitives.asymmetric import ec as _ec
            from cryptography.hazmat.primitives.serialization import load_pem_public_key as _load_pub

            pub = _load_pub(public_pem.encode("utf-8"))
            if not isinstance(pub, _ec.EllipticCurvePublicKey):
                return None
            if not isinstance(pub.curve, _ec.SECP256R1):
                return None
            pub_key = pub
        except Exception:
            return None
    else:
        return None

    numbers = pub_key.public_numbers()
    x = numbers.x.to_bytes(32, byteorder="big")
    y = numbers.y.to_bytes(32, byteorder="big")

    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64url_nopad(x),
        "y": _b64url_nopad(y),
        "alg": "ES256",
        "use": "sig",
    }
    if kid:
        jwk["kid"] = kid
    return jwk


def derive_jwks_from_env(env: Dict[str, str]) -> Dict[str, Any]:
    """Build a JWKS from environment variables.

    Priority order:
      1) MANIFEST_JWKS_JSON (full JWKS JSON)
      2) Derive from MANIFEST_PUBLIC_KEY_PEM or MANIFEST_PRIVATE_KEY_PEM (EC P-256)
    """
    jwks_json = env.get("MANIFEST_JWKS_JSON")
    if jwks_json:
        try:
            import json

            data = json.loads(jwks_json)
            if isinstance(data, dict) and "keys" in data:
                return data
        except Exception:
            pass

    kid = env.get("MANIFEST_KEY_ID") or "dev-key"
    pub_pem = env.get("MANIFEST_PUBLIC_KEY_PEM")
    priv_pem = env.get("MANIFEST_PRIVATE_KEY_PEM")

    jwk = derive_ec_p256_jwk_from_pem(private_pem=priv_pem, public_pem=pub_pem, kid=kid)
    if jwk:
        return {"keys": [jwk]}

    return {"keys": []}


def ec_p256_jwk_to_public_pem(jwk: Dict[str, Any]) -> Optional[str]:
    """Convert an EC P-256 JWK to a PEM-encoded public key."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec as _ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        import base64

        if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
            return None
        x_b = base64.urlsafe_b64decode(jwk["x"] + "==")
        y_b = base64.urlsafe_b64decode(jwk["y"] + "==")
        x = int.from_bytes(x_b, byteorder="big")
        y = int.from_bytes(y_b, byteorder="big")
        pub_numbers = _ec.EllipticCurvePublicNumbers(x, y, _ec.SECP256R1())
        pub_key = pub_numbers.public_key()
        pem = pub_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        return pem.decode("utf-8")
    except Exception:
        return None

