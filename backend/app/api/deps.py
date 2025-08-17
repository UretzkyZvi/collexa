from fastapi import Depends, HTTPException, Header, Request
from typing import Optional, Dict, Any

# Import module to simplify monkeypatching in tests
from app.security import stack_auth
from app.db.session import get_db, set_rls_for_session
from sqlalchemy.orm import Session


async def require_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_team_id: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """General auth: verifies token and determines org scope.
    May derive org_id from profile if X-Team-Id is not provided.
    """
    # If auth middleware already validated and attached context, reuse it
    if getattr(request.state, "auth", None):
        ctx = request.state.auth
        set_rls_for_session(db, ctx.get("org_id"))
        return ctx

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    profile = stack_auth.verify_stack_access_token(token)
    user_id = profile.get("id") or profile.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token (no user id)")

    org_id = None
    if x_team_id:
        stack_auth.verify_team_membership(x_team_id, token)
        org_id = x_team_id

    if not org_id:
        org_id = (
            profile.get("selectedTeamId")
            or profile.get("team_id")
            or profile.get("org_id")
            or user_id
        )

    set_rls_for_session(db, org_id)

    ctx = {
        "user_id": user_id,
        "org_id": org_id,
        "profile": profile,
        "access_token": token,
    }
    request.state.auth = ctx
    return ctx


async def require_team(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_team_id: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Stricter auth for sensitive endpoints: requires explicit X-Team-Id.
    Verifies team membership and scopes org_id to that team.
    """
    if not x_team_id:
        raise HTTPException(status_code=400, detail="X-Team-Id header is required")

    # Reuse existing auth context if present
    ctx = getattr(request.state, "auth", None)
    if ctx and ctx.get("access_token"):
        # Ensure membership for the requested team and override org_id
        stack_auth.verify_team_membership(
            x_team_id, ctx["access_token"]
        )  # may raise 403
        ctx = {**ctx, "org_id": x_team_id}
        request.state.auth = ctx
        set_rls_for_session(db, x_team_id)
        return ctx

    # Fallback to verifying token from header
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    profile = stack_auth.verify_stack_access_token(token)
    user_id = profile.get("id") or profile.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token (no user id)")

    stack_auth.verify_team_membership(x_team_id, token)  # may raise 403
    set_rls_for_session(db, x_team_id)

    ctx = {
        "user_id": user_id,
        "org_id": x_team_id,
        "profile": profile,
        "access_token": token,
    }
    request.state.auth = ctx
    return ctx
