# Ensure 'app' package is importable when running pytest from backend/
import os
import sys
import pytest
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# Ensure tables exist for tests using SQLite; safe no-op for Postgres if managed externally
@pytest.fixture(autouse=True, scope="function")
def _ensure_tables():
    try:
        from app.db.session import Base, engine
        from app.db import models  # noqa: F401 ensure models are registered

        Base.metadata.create_all(bind=engine)
        yield
    finally:
        try:
            Base.metadata.drop_all(bind=engine)
        except Exception:
            pass


@pytest.fixture
def mock_auth():
    """Mock authentication that returns valid org/user info."""
    return {"org_id": "test-org", "user_id": "test-user", "selectedTeamId": "test-org"}


@pytest.fixture
def mock_stack_auth_global(monkeypatch):
    """Global mock for stack auth that works with middleware."""
    from app.security import stack_auth

    def fake_verify_token(token: str):
        # Default mock behavior - can be overridden in specific tests
        if token in ["user1-token", "fake-token", "fake"]:
            return {"id": "user1", "selectedTeamId": "org1"}
        elif token == "user2-token":
            return {"id": "user2", "selectedTeamId": "org2"}
        else:
            raise Exception("Invalid token")

    def fake_verify_team(team_id: str, token: str):
        # Default mock behavior - can be overridden in specific tests
        if token in ["user1-token", "fake-token", "fake"] and team_id in ["org1", "o1"]:
            return {"id": team_id}
        elif token == "user2-token" and team_id in ["org2", "o2"]:
            return {"id": team_id}
        else:
            raise Exception("Not a member")

    # Apply the mocks
    monkeypatch.setattr(stack_auth, "verify_stack_access_token", fake_verify_token)
    monkeypatch.setattr(stack_auth, "verify_team_membership", fake_verify_team)

    return {
        "verify_token": fake_verify_token,
        "verify_team": fake_verify_team
    }


@pytest.fixture
def mock_db():
    """Mock database session."""
    mock = MagicMock()
    mock.query.return_value = mock
    mock.filter.return_value = mock
    mock.order_by.return_value = mock
    mock.limit.return_value = mock
    mock.offset.return_value = mock
    mock.all.return_value = []
    mock.first.return_value = None
    mock.count.return_value = 0
    return mock


@pytest.fixture(autouse=True)
def override_get_db_when_mock_requested(request):
    """If a test requests the 'mock_db' fixture, override FastAPI get_db dependency
    to use that mock for the duration of the test.
    """
    if "mock_db" in request.fixturenames:
        from app.main import app
        from app.api.deps import get_db

        mock_db = request.getfixturevalue("mock_db")

        def _get_mock_db():
            return mock_db

        app.dependency_overrides[get_db] = _get_mock_db
        try:
            yield
        finally:
            app.dependency_overrides.pop(get_db, None)
    else:
        # No-op for tests that don't use mock_db
        yield
