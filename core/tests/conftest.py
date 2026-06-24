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

    # Point the Studio Engine's local export folders at a throwaway temp dir so
    # tests never write into the developer's ./exports tree.
    monkeypatch.setenv("INVISABLE_EXPORT_DIR", str(tmp_path / "exports"))

    from invisable_os.store import db, repository
    from invisable_os.studio import store as studio_store

    db.reset_engine()
    repository._singleton = None  # drop the cached repository singleton
    studio_store.reset_studio_store()  # drop the cached studio store singleton
    db.init_db()
    yield
    db.reset_engine()
    studio_store.reset_studio_store()
