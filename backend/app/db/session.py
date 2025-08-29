from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool
from typing import Optional
import os

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./dev.db"


class Base(DeclarativeBase):
    pass


# Create engine with sane defaults for sqlite (esp. in-memory for tests)
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if ":memory:" in DATABASE_URL:
        engine = create_engine(
            DATABASE_URL,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(
            DATABASE_URL,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_rls_for_session(db, org_id: Optional[str]):
    """Optional: set a local session variable for Postgres RLS policies.
    Safe to call even if org_id is None or if DB doesn't have the setting.
    """
    if not org_id:
        return
    try:
        db.execute(text("SET LOCAL app.org_id = :org_id"), {"org_id": org_id})
    except Exception:
        # ignore if extension/setting not present yet
        pass
