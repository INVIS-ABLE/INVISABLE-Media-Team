"""Alembic migrations provision the full schema and reverse cleanly.

Proves `alembic upgrade head` builds every app table from an empty database (so
production can migrate Postgres instead of relying on create_all), and that
`downgrade base` tears it back down. Runs on a throwaway SQLite file.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

CORE = Path(__file__).resolve().parents[1]


def _config() -> Config:
    cfg = Config(str(CORE / "alembic.ini"))
    cfg.set_main_option("script_location", str(CORE / "migrations"))
    return cfg


def _tables(db_path: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_head_then_downgrade_base(tmp_path, monkeypatch):
    db_path = tmp_path / "migrated.db"
    monkeypatch.setenv("INVISABLE_SQLITE_PATH", str(db_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from invisable_os.store import db as dbmod

    dbmod.reset_engine()

    cfg = _config()
    command.upgrade(cfg, "head")

    tables = _tables(db_path)
    # A representative spread across content lifecycle, recognition, and consent.
    assert {
        "queue_item",
        "founder_recognition_row",
        "person_row",
        "relationship_touch",
        "community_story",
        "alembic_version",
    } <= tables

    command.downgrade(cfg, "base")
    after = _tables(db_path)
    assert "queue_item" not in after
    assert "person_row" not in after

    dbmod.reset_engine()
