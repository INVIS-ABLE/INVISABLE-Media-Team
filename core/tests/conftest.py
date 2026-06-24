"""Test fixtures.

Every test runs against a throwaway SQLite database in a temp directory, so the
persistence layer is exercised for real without touching the developer's ./data DB
and without any cross-test contamination.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("INVISABLE_SQLITE_PATH", str(db_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from invisable_os.store import db, repository

    db.reset_engine()
    repository._singleton = None  # drop the cached repository singleton
    db.init_db()
    yield
    db.reset_engine()
