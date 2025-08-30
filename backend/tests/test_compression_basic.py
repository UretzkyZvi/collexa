import json
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def test_engine_noop_when_deps_missing():
    from app.services.compression.basic_engine import BasicCompressionEngine

    engine = BasicCompressionEngine(zstd_compressor=None)
    obj = {"a": 1, "b": "x"}
    res = engine.compress(obj)
    assert res.data  # bytes
    # method will be either "msgpack" if msgpack installed, or "noop" otherwise
    assert res.method in ("msgpack", "noop")
    roundtrip = engine.decompress(res)
    assert roundtrip == obj


def test_response_opt_in_compression_header(client):
    # Add middleware if not already present (app created at import time)
    from app.main import app as fastapi_app
    from app.middleware.compression_middleware import CompressionMiddleware

    # Ensure middleware added once for test context (avoid adding after app start)
    um = getattr(fastapi_app, "user_middleware", [])
    already = any(getattr(m, "cls", None) is CompressionMiddleware for m in um)
    if not already and fastapi_app.middleware_stack is None:
        fastapi_app.add_middleware(CompressionMiddleware)

    # Call a simple JSON endpoint with header to accept compression
    resp = client.get("/health", headers={"X-Accept-Compression": "zstd"})
    assert resp.status_code == 200
    # On success path, middleware may convert to octet-stream with encoding header
    # If zstd/msgpack missing, middleware should fall back and keep JSON content-type
    enc = resp.headers.get("content-encoding")
    if enc:
        assert enc in ("zstd+msgpack", "msgpack")
        assert resp.headers.get("content-type") == "application/octet-stream"
        assert isinstance(resp.content, (bytes, bytearray))
    else:
        # No compression applied (e.g., deps missing) -> JSON
        assert resp.headers.get("content-type", "").startswith("application/json")
        assert resp.json()["status"] == "ok"

