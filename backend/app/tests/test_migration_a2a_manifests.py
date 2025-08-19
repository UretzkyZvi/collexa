from sqlalchemy import inspect
from app.db.session import engine


def test_a2a_manifests_table_exists():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert 'a2a_manifests' in tables

