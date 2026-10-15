"""SQLAlchemy engine and session factory."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

engine = None
SessionLocal: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


def _connect():
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite"):
        raw = url.removeprefix("sqlite:///")
        if raw and raw != ":memory:":
            Path(raw).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}
    eng = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    factory = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    return eng, factory


def init_engine() -> None:
    """Bind the process-wide engine. Safe to call again after settings change."""
    global engine, SessionLocal
    engine, SessionLocal = _connect()


def init_db() -> None:
    from app import models  # noqa: F401
    from app.seed import seed_if_empty

    if engine is None or SessionLocal is None:
        init_engine()
    assert engine is not None and SessionLocal is not None
    Base.metadata.create_all(engine)
    _ensure_profile_style()
    db = SessionLocal()
    try:
        seed_if_empty(db)
        db.commit()
    finally:
        db.close()


# Created at import so other modules receive the live session factory,
# not a None placeholder captured before init_db runs.
init_engine()


def _ensure_profile_style() -> None:
    """Add the Graves style JSON column to databases created before it existed."""
    assert engine is not None
    tables = inspect(engine).get_table_names()
    if "profiles" not in tables:
        return
    columns = {column["name"] for column in inspect(engine).get_columns("profiles")}
    if "style" in columns:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE profiles ADD COLUMN style JSON"))


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        init_engine()
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
