import time
import uuid
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db import models


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Audit middleware that logs API calls with actor, endpoint, status, and metadata.
    Captures all /v1/* endpoints except health/docs.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ):
        path = request.url.path
        
        # Skip non-API paths
        if not path.startswith("/v1") or path in ["/v1/health"]:
            return await call_next(request)

        # Generate request ID for correlation
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        # Get client info
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Capture request body for capability extraction (for invoke endpoints)
        request_body = None
        if path.endswith("/invoke"):
            try:
                body = await request.body()
                request_body = body.decode("utf-8") if body else None
                # Re-create request with body for downstream processing
                from starlette.requests import Request as StarletteRequest
                scope = request.scope.copy()
                receive = request.receive
                # Store body for later use
                request.state._body = request_body
            except:
                pass

        # Process request
        response = await call_next(request)
        
        # Extract audit info from auth context
        auth_ctx = getattr(request.state, "auth", {})
        org_id = auth_ctx.get("org_id")
        actor_id = auth_ctx.get("user_id")
        
        # For API key auth, use "api_key" as actor
        if auth_ctx.get("profile", {}).get("auth") == "api_key":
            actor_id = "api_key"
        
        # Extract agent_id from path if present
        agent_id = None
        if "/agents/" in path:
            parts = path.split("/agents/")
            if len(parts) > 1:
                agent_id = parts[1].split("/")[0]
        
        # Extract capability from request body for invoke endpoints
        capability = None
        if path.endswith("/invoke") and hasattr(request.state, "_body"):
            try:
                import json
                body = json.loads(request.state._body)
                capability = body.get("capability")
            except:
                pass
        
        # Log to database (async, don't block response)
        if org_id:  # Only log if we have org context
            try:
                db: Session = SessionLocal()
                audit_log = models.AuditLog(
                    org_id=org_id,
                    actor_id=actor_id,
                    endpoint=f"{request.method} {path}",
                    agent_id=agent_id,
                    capability=capability,
                    status_code=response.status_code,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                db.add(audit_log)
                db.commit()
                db.close()
            except Exception:
                # Don't fail the request if audit logging fails
                pass
        
        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = request_id
        
        return response
