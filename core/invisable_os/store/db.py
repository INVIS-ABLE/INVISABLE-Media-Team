"""Database engine & session management.

Resolution:
* ``DATABASE_URL`` if set (Postgres in production — ``+asyncpg`` is normalised to the
  sync ``+psycopg`` driver this layer uses).
* otherwise a local SQLite file at ``INVISABLE_SQLITE_PATH`` (default ``./data/invisable.db``).

The app owns its tables via :func:`init_db` (SQLAlchemy ``create_all``), so it boots
on a clean database with no manual migration step. ``db/schema.sql`` remains the
canonical, richly-typed Postgres DDL for direct/BI use.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine = None
_Session: sessionmaker | None = None


def _resolve_url() -> str:
    raw = os.getenv("DATABASE_URL")
    if raw:
        # This layer is synchronous; normalise an async DSN to the sync driver.
        return raw.replace("+asyncpg", "+psycopg")
    path = os.getenv("INVISABLE_SQLITE_PATH", "./data/invisable.db")
    if path != ":memory:":
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
    return f"sqlite:///{path}"


def get_engine():
    global _engine
    if _engine is None:
        url = _resolve_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, future=True, connect_args=connect_args)
    return _engine


def reset_engine() -> None:
    """Dispose the engine/session so a new ``DATABASE_URL`` takes effect (tests)."""
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Session = None


def init_db() -> None:
    """Create all application tables if they do not already exist."""
    from invisable_os.store import models  # noqa: F401  (registers the mappers)

    Base.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Session:
    """Transactional session scope: commit on success, rollback on error."""
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
