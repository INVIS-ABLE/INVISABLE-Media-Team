"""Persistence layer.

Operational by default: with no configuration the platform persists to a local
SQLite database (no server required), so the queue, tag network, partners, and
opportunities survive restarts. Point ``DATABASE_URL`` at Postgres for production —
the same ORM and repository work unchanged.
"""

from invisable_os.store.db import init_db, reset_engine, session_scope
from invisable_os.store.repository import Repository, get_repository

__all__ = ["init_db", "reset_engine", "session_scope", "Repository", "get_repository"]
