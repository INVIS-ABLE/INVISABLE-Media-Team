"""Smart posting times: learn when content performs and suggest the best slots."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from invisable_os.engines import rank_posting_slots
from invisable_os.main import app
from invisable_os.models.content import QueueStatus
from invisable_os.services import suggest_post_times
from invisable_os.store import get_repository

client = TestClient(app)


# --- pure ranking -----------------------------------------------------------


def test_rank_prefers_higher_engagement_slot():
    obs = [
        {"weekday": 3, "hour": 19, "value": 100},  # Thu 19:00 — strong
        {"weekday": 3, "hour": 19, "value": 120},
        {"weekday": 1, "hour": 9, "value": 20},    # Tue 09:00 — weak
        {"weekday": 1, "hour": 9, "value": 30},
    ]
    slots = rank_posting_slots(obs, top=2)
    assert slots[0]["label"] == "Thu 19:00"
    assert slots[0]["lift_pct"] > 0
    assert slots[0]["samples"] == 2


def test_rank_requires_min_samples():
    obs = [{"weekday": 3, "hour": 19, "value": 100}]  # only one data point
    assert rank_posting_slots(obs) == []


def test_rank_empty():
    assert rank_posting_slots([]) == []


# --- service (joins published_at to signals) --------------------------------


def test_suggest_post_times_learns_from_history():
    repo = get_repository()
    # Two posts published Thu 19:00 that did well, two Tue 09:00 that did poorly.
    thu = datetime(2026, 6, 18, 19, 0, tzinfo=UTC)   # Thursday
    tue = datetime(2026, 6, 16, 9, 0, tzinfo=UTC)    # Tuesday
    plan = [("p1", thu, 100), ("p2", thu, 120), ("p3", tue, 10), ("p4", tue, 20)]
    for cid, when, value in plan:
        item_id = repo.enqueue({
            "candidate_id": cid,
            "candidate": {"hook": "h", "platform": "tiktok", "themes": ["founder"]},
            "status": QueueStatus.PUBLISHED.value,
            "platform": "tiktok",
        })
        repo.transition(item_id, QueueStatus.PUBLISHED, published_at=when)
        repo.record_signal(cid, "tiktok", "saves", value, ["founder"])

    out = suggest_post_times(platform="tiktok")
    assert out["observations"] == 4
    assert out["suggestions"][0]["label"] == "Thu 19:00"


def test_suggest_post_times_missing_item():
    assert "error" in suggest_post_times(item_id="nope")


def test_suggest_post_times_empty_history():
    out = suggest_post_times(platform="tiktok")
    assert out["observations"] == 0
    assert out["suggestions"] == []


# --- endpoint ---------------------------------------------------------------


def test_scheduling_suggest_endpoint():
    r = client.get("/v1/scheduling/suggest?platform=instagram")
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"platform", "observations", "suggestions"}
