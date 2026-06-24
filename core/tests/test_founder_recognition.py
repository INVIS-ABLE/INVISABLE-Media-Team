"""Phase 1 additions ported onto the operational store:

* Founder Recognition Index ledger (persisted on Watchtower ingest + read API).
* Cross-run founder-presence seeding for the daily pipeline.

The autouse ``isolated_db`` fixture (see conftest) gives each test a throwaway
SQLite database, so these exercise the real persistence layer.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import create_app
from invisable_os.models.content import ContentCandidate, Platform, QueueStatus
from invisable_os.services import run_and_queue_daily
from invisable_os.store import get_repository


def _client() -> TestClient:
    return TestClient(create_app())


# -- Founder Recognition ledger ---------------------------------------------


def test_founder_recognition_history_accumulates_chronologically():
    repo = get_repository()
    repo.record_founder_recognition(0.10, {"media_mentions": 1})
    repo.record_founder_recognition(0.42, {"media_mentions": 6})
    history = repo.list_founder_recognition()
    assert [round(h["index_value"], 2) for h in history] == [0.10, 0.42]
    assert history[-1]["breakdown"]["media_mentions"] == 6


def test_watchtower_ingest_persists_signals_and_index():
    client = _client()

    def ingest(mentions: float) -> float:
        body = {
            "signals": [
                {
                    "candidate_id": "c1",
                    "platform": "instagram",
                    "metric": "media_mentions",
                    "value": mentions,
                }
            ]
        }
        return client.post("/v1/watchtower/ingest", json=body).json()[
            "founder_recognition_index"
        ]

    low = ingest(1)
    high = ingest(20)
    assert high > low

    recog = client.get("/v1/founder/recognition").json()
    assert recog["points"] == 2
    assert recog["latest"] == high
    # The raw signals were persisted too.
    from invisable_os.store.db import session_scope
    from invisable_os.store.models import PerfSignalRow

    with session_scope() as s:
        assert s.query(PerfSignalRow).count() == 2


def test_founder_recognition_empty_history():
    recog = _client().get("/v1/founder/recognition").json()
    assert recog == {"latest": 0.0, "points": 0, "history": []}


# -- Cross-run founder-presence seeding -------------------------------------


def test_recent_candidates_seed_excludes_rejected():
    repo = get_repository()
    keep = repo.enqueue(
        {
            "candidate_id": "keep",
            "candidate": ContentCandidate(
                brief="b", platform=Platform.INSTAGRAM, founder_centred=True
            ).model_dump(),
            "platform": "instagram",
        }
    )
    drop = repo.enqueue(
        {
            "candidate_id": "drop",
            "candidate": ContentCandidate(brief="b", platform=Platform.INSTAGRAM).model_dump(),
            "platform": "instagram",
        }
    )
    repo.transition(drop, QueueStatus.REJECTED)

    assert repo.get_queue_item(keep)["candidate_id"] == "keep"  # sanity
    # Rejected items are not used to seed the next run — only the kept founder one.
    recent = repo.recent_candidates()
    assert len(recent) == 1
    assert recent[0]["founder_centred"] is True


def test_daily_pipeline_consumes_prior_published_seed():
    # Two consecutive persisted runs: the second seeds from the first without error
    # and the queue accumulates both days.
    first = run_and_queue_daily(candidates_per_slot=6)
    second = run_and_queue_daily(candidates_per_slot=6)
    assert first["total"] == second["total"] == 20
    assert len(get_repository().list_queue(limit=100)) == 40
