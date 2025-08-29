"""
Compression-aware middleware (opt-in via header) for SC.1-01.

- When the request includes `X-Compress-Request: true`, we will try to decode
  a compressed JSON body using BasicCompressionEngine.
- When the response is JSON and the client sends `X-Accept-Compression: zstd`
  we compress the response payload and set `Content-Encoding: zstd+msgpack`.

This is minimal scaffolding to exercise the compression engine. It is safe to
keep disabled by default; only engages on explicit headers.
"""

from __future__ import annotations

from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json

from app.services.compression.basic_engine import BasicCompressionEngine
from app.services.compression.dictionary_trainer import ZstdDictionaryTrainer


class CompressionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Engine is initialized in startup and stored on ASGI scope app.state. During tests
        # the ASGI app may be wrapped by Starlette middlewares that don't expose .state.
        # We'll lazily read from request.app.state in dispatch if available.
        self._engine = BasicCompressionEngine()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        # Refresh engine from ASGI app.state if available (works in tests & prod)
        try:
            app_obj = request.app  # FastAPI/Starlette app
            engine = getattr(getattr(app_obj, "state", object()), "compression_engine", None)
            if engine is not None:
                self._engine = engine
        except Exception:
            pass

        # Request-side optional decompression
        if request.headers.get("X-Compress-Request", "").lower() == "true":
            try:
                body = await request.body()
                decoded = self._engine.decompress(
                    type("Comp", (), {"method": "zstd+msgpack", "data": body})
                )
                request._body = json.dumps(decoded).encode("utf-8")  # type: ignore[attr-defined]
            except Exception:
                pass

        response = await call_next(request)

        # Response-side optional compression
        if request.headers.get("X-Accept-Compression", "").lower() == "zstd":
            try:
                if response.headers.get("content-type", "").startswith("application/json"):
                    if hasattr(response, "body_iterator"):
                        body_bytes = b"".join([chunk async for chunk in response.body_iterator])
                    else:
                        body_bytes = getattr(response, "body", b"") or b""

                    payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                    comp = self._engine.compress(payload)

                    comp_resp = Response(content=comp.data)
                    comp_resp.headers["Content-Type"] = "application/octet-stream"
                    comp_resp.headers["Content-Encoding"] = comp.method
                    return comp_resp
            except Exception:
                return response

        return response

