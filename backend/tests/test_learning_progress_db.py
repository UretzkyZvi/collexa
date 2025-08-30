import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.db import models


def _create_agent_and_sandbox(db: Session) -> tuple[str, str]:
    agent = models.Agent(id="agent-db", org_id="org-db")
    db.add(agent)
    db.flush()
    sandbox = models.Sandbox(id="sb-db", agent_id=agent.id, org_id=agent.org_id, mode="mock", status="created")
    db.add(sandbox)
    db.commit()
    return agent.id, sandbox.id


def test_learning_iteration_persists_sandbox_run_when_db_and_sandbox_provided():
    client = TestClient(app)

    # Setup DB state
    db = SessionLocal()
    try:
        agent_id, sandbox_id = _create_agent_and_sandbox(db)
    finally:
        db.close()

    # Trigger a dev iteration (endpoint uses in-memory flow; we will call learning loop directly for DB injection)
    from app.services.learning.learning_loop import run_learning_iteration, IterationConfig

    cfg = IterationConfig(agent_id=agent_id, tasks=["http test"], docs=[], sandbox_mode="mock")

    # Use a new session for persistence
    db2 = SessionLocal()
    try:
        session = run_learning_iteration(cfg, db=db2, org_id="org-db", sandbox_id=sandbox_id)
        assert session.tests[1] == 1

        # Verify SandboxRun persisted
        runs = db2.query(models.SandboxRun).filter(models.SandboxRun.sandbox_id == sandbox_id).all()
        assert len(runs) == 1
        assert runs[0].status in ("completed", "failed")
        assert runs[0].phase == "learn"
        assert runs[0].task_name is not None
    finally:
        db2.close()

