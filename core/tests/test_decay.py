"""Tests for the Content Decay Detector.

Deterministic, read-only analysis over the queue + War Chest: it flags overused
hooks, near-duplicate posts, expired reserve stock, category crowding and stale
hashtags — and a clean, varied feed produces no flags.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services import detect_decay
from invisable_os.store import get_repository


def _enqueue(repo, hook, body="", pillar="humour", tags=None):
    return repo.enqueue({
        "candidate": {"hook": hook, "body": body, "hashtags": tags or []},
        "pillar": pillar,
        "platform": "tiktok",
    })


def test_clean_varied_feed_has_no_flags():
    repo = get_repository()
    varied = [
        ("Tool theft hit my van again", "scaffolders rallied round to lend kit overnight"),
        ("Pacing beats pushing through", "small kind adjustments add up across a long week"),
        ("Why I started this movement", "to make unseen conditions visible without overclaiming"),
        ("Site banter saved my Monday", "the lads noticed I was quiet and just made tea"),
    ]
    for hook, body in varied:
        _enqueue(repo, hook, body)
    report = detect_decay().as_dict()
    assert report["ok"] is True
    assert report["flag_count"] == 0
    assert report["scanned"]["queue"] == 4


def test_overused_hook_is_flagged():
    repo = get_repository()
    for _ in range(4):
        _enqueue(repo, "Nobody talks about chronic fatigue")
    report = detect_decay()
    kinds = {f.kind for f in report.flags}
    assert "overused_hook" in kinds


def test_near_duplicate_posts_are_flagged():
    repo = get_repository()
    body = "looking fine and being fine are not the same thing at all really"
    _enqueue(repo, "When the job starts at seven", body)
    _enqueue(repo, "When the job starts at seven am", body)
    report = detect_decay()
    assert any(f.kind == "near_duplicate" for f in report.flags)


def test_expired_reserve_is_flagged():
    repo = get_repository()
    repo.add_war_chest_item({
        "title": "stale", "category": "humour", "reserve_status": "ready",
        "expiry_date": datetime.now(UTC) - timedelta(days=2),
    })
    report = detect_decay()
    assert any(f.kind == "expired_reserve" for f in report.flags)


def test_category_dominance_is_flagged():
    repo = get_repository()
    for _ in range(8):
        repo.add_war_chest_item({"title": "h", "category": "humour", "reserve_status": "ready"})
    report = detect_decay()
    assert any(f.kind == "category_dominance" for f in report.flags)


def test_overused_hashtag_is_flagged():
    repo = get_repository()
    for i in range(8):
        _enqueue(repo, f"hook {i}", f"body {i}", tags=["#INVISABLE", f"#topic{i}"])
    report = detect_decay()
    assert any(f.kind == "stale_hashtag" for f in report.flags)


def test_decay_api():
    client = TestClient(app)
    repo = get_repository()
    for _ in range(4):
        _enqueue(repo, "Exactly the same hook every time")
    body = client.get("/v1/decay/scan").json()
    assert body["ok"] is False
    assert "overused_hook" in body["by_kind"]
