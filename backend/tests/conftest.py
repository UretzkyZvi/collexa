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
