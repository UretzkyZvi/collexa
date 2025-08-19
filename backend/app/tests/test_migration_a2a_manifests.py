import os
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("DATABASE_URL", "").startswith("sqlite"),
    reason="Skip migration-dependent test on sqlite dev DB; run in CI with Postgres",
)

from sqlalchemy import create_engine, inspect


def test_a2a_manifests_table_exists():
    engine = create_engine(os.environ["DATABASE_URL"])  # provided in CI
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "a2a_manifests" in tables

