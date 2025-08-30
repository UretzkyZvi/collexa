"""
Learning progress tracking helpers for N.2.

This module provides a minimal, safe-by-default interface for recording
progress of learning iterations. It deliberately avoids hard dependencies
on external services or database state so it can be imported in dev/test
contexts without configuration.

- record_iteration: lightweight hook invoked by the learning loop
  - Emits optional metrics via app.services.compression.tracking (MLflow-safe)
  - Optionally persists SandboxRun rows if a DB session and sandbox_id are provided
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

try:
    # Optional imports for DB persistence
    from sqlalchemy.orm import Session
    from app.db import models
    from app.db.session import set_rls_for_session
except Exception:  # pragma: no cover - allow import without SQLAlchemy in tests
    Session = object  # type: ignore
    models = None  # type: ignore
    def set_rls_for_session(db, org_id: Optional[str]):
        return None

from app.services.compression.tracking import run as tracking_run, log_metrics


def record_iteration(
    *,
    agent_id: str,
    sandbox_mode: str,
    task_name: str,
    success: bool,
    errors: Dict[str, int] | None,
    tool_usage: Dict[str, Any] | None,
    db: Optional["Session"] = None,
    org_id: Optional[str] = None,
    sandbox_id: Optional[str] = None,
) -> None:
    """Record progress for a single learning iteration.

    Safe defaults:
    - Always emit basic metrics (guarded) for observability
    - Only attempt DB writes when db and sandbox_id are provided and models are available
    - Fail-closed: catch and ignore persistence errors so learning isn't blocked
    """
    # Metrics (safe no-op if tracking backend not configured)
    try:
        with tracking_run("learning_progress", tags={"agent_id": agent_id, "mode": sandbox_mode}):
            log_metrics(
                {
                    "success": 1.0 if success else 0.0,
                    "errors_count": float(sum((errors or {}).values())),
                }
            )
    except Exception:
        pass

    # Optional DB persistence of sandbox_runs
    if db is None or sandbox_id is None or models is None:  # type: ignore
        return

    try:
        # Ensure tenant isolation if provided
        set_rls_for_session(db, org_id)

        run = models.SandboxRun(  # type: ignore[attr-defined]
            sandbox_id=sandbox_id,
            phase="learn",
            task_name=task_name,
            status="completed" if success else "failed",
            input_json={"tool": tool_usage or {}, "mode": sandbox_mode},
            output_json={"errors": errors or {}},
            error_json=None if success else {"errors": errors or {}},
            finished_at=datetime.utcnow(),
        )
        db.add(run)
        db.commit()
    except Exception:
        # Do not raise from progress tracking; keep learning flow resilient
        try:
            db.rollback()  # type: ignore
        except Exception:
            pass
        return

