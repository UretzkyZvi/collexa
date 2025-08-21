from sqlalchemy import create_engine, inspect
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL", "").startswith("sqlite"),
    reason="Skip: requires DATABASE_URL (Postgres) in CI",
)


def test_a2a_manifests_table_exists():
    db_url = os.getenv("DATABASE_URL")
    assert db_url, "DATABASE_URL must be set in CI for migration tests"
    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "a2a_manifests" in tables
