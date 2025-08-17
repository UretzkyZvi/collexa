from typing import Callable, Awaitable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

# Import module, not symbols, so tests can monkeypatch reliably
from app.security import stack_auth

PUBLIC_PREFIXES = (
    "/health",
    "/docs",
    "/openapi.json",
    "/v1/.well-known",  # public descriptor endpoints
)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Coarse auth middleware:
    - For /v1/* endpoints (except public prefixes), require a Bearer token
    - Verifies token (and optional team membership via X-Team-Id)
    - Attaches auth context to request.state.auth for downstream usage

    Note: DB RLS scoping is still performed in require_auth dependency.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ):
        path = request.url.path

        # Only guard API v1 (skip known public paths)
        if path.startswith("/v1") and not any(
            path.startswith(p) for p in PUBLIC_PREFIXES
        ):
            authz = request.headers.get("authorization", "")
            if not authz.lower().startswith("bearer "):
                return JSONResponse({"detail": "Missing bearer token"}, status_code=401)

            token = authz.split(" ", 1)[1]
            try:
                profile = stack_auth.verify_stack_access_token(token)
            except Exception:
                return JSONResponse(
                    {"detail": "Invalid or expired access token"}, status_code=401
                )

            user_id = profile.get("id") or profile.get("user_id")
            if not user_id:
                return JSONResponse(
                    {"detail": "Invalid token (no user id)"}, status_code=401
                )

            org_id = None
            team_id = request.headers.get("x-team-id")
            if team_id:
                try:
                    stack_auth.verify_team_membership(team_id, token)
                    org_id = team_id
                except Exception:
                    return JSONResponse(
                        {"detail": "Not a member of this team"}, status_code=403
                    )

            if not org_id:
                org_id = (
                    profile.get("selectedTeamId")
                    or profile.get("team_id")
                    or profile.get("org_id")
                    or user_id
                )

            # Attach context for dependencies/handlers
            request.state.auth = {
                "user_id": user_id,
                "org_id": org_id,
                "profile": profile,
                "access_token": token,
            }

        return await call_next(request)
