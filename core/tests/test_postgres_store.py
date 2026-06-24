"""Repository round-trip against real PostgreSQL.

The rest of the suite runs on SQLite; this proves the same ORM + repository work on
Postgres (JSON columns, status filters, ordering). Skipped unless ``TEST_DATABASE_URL``
points at a reachable Postgres — CI sets it via a postgres service; locally it's a
no-op. It re-points the engine inside the test (the autouse fixture forces SQLite),
then restores it.
"""

from __future__ import annotations

import os

import pytest

from invisable_os.models.content import QueueStatus
from invisable_os.models.departments import Person

PG_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def pg_repo(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", PG_URL)
    from invisable_os.store import db as dbmod
    from invisable_os.store import repository as repomod

    dbmod.reset_engine()
    repomod._singleton = None
    # Clean slate, then provision the schema on Postgres.
    from invisable_os.store.db import Base, get_engine

    Base.metadata.drop_all(get_engine())
    dbmod.init_db()
    yield repomod.get_repository()
    Base.metadata.drop_all(get_engine())
    dbmod.reset_engine()
    repomod._singleton = None


def test_queue_lifecycle_on_postgres(pg_repo):
    item_id = pg_repo.enqueue(
        {
            "candidate_id": "c1",
            "candidate": {"hook": "h", "founder_centred": True, "themes": ["a", "b"]},
            "status": QueueStatus.PENDING_REVIEW.value,
            "platform": "instagram",
            "pillar": "education",
        }
    )
    assert pg_repo.counts_by_status().get("pending_review") == 1

    pg_repo.transition(item_id, QueueStatus.APPROVED)
    assert pg_repo.list_queue(status="approved")[0]["id"] == item_id
    # JSON column survives the Postgres round-trip.
    assert pg_repo.get_queue_item(item_id)["candidate"]["themes"] == ["a", "b"]


def test_person_consent_and_recognition_on_postgres(pg_repo):
    pid = pg_repo.add_person(Person(full_name="Jane Doe", role="ambassador"))
    pg_repo.set_consent(pid, "approved", allowed_platforms=["instagram"])
    assert pg_repo.get_person(pid)["consent_status"] == "approved"

    pg_repo.record_founder_recognition(0.42, {"media_mentions": 6})
    history = pg_repo.list_founder_recognition()
    assert history[-1]["index_value"] == 0.42
    assert history[-1]["breakdown"]["media_mentions"] == 6
