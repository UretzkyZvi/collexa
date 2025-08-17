# Ensure 'app' package is importable when running pytest from backend/
import os
import sys
import pytest

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

