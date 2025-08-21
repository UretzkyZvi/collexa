"""
Shared HTTPX AsyncClient with connection pooling and sane timeouts.

Use get_http_client() to obtain the singleton client.
Start/stop handled from app.startup lifespan.
"""

from typing import Optional
import httpx

_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=0.5, read=1.5, write=1.5, pool=2.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            headers={"User-Agent": "collexa-backend/1.0"},
        )
    return _client


async def close_http_client():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
