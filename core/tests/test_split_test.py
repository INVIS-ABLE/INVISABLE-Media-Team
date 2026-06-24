"""Tests for Format Split Testing.

One idea, several formats, head-to-head — then learn which format wins from the
signals the Watchtower records. Everything is deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.models.content import ContentFormat, Platform
from invisable_os.services.split_test import (
    DEFAULT_SPLIT_FORMATS,
    build_split,
    format_leaderboard,
)
from invisable_os.store import get_repository

client = TestClient(app)


# --- building a split -------------------------------------------------------


def test_split_builds_one_variant_per_format():
    split = build_split("pacing on a busy week in the trades")
    assert len(split["variants"]) == len(DEFAULT_SPLIT_FORMATS)
    formats = {v["format"] for v in split["variants"]}
    assert formats == {f.value for f in DEFAULT_SPLIT_FORMATS}
    assert split["experiment_id"]


def test_split_honours_requested_formats_and_dedupes():
    split = build_split(
        "tool theft awareness",
        formats=[ContentFormat.IMAGE, ContentFormat.IMAGE, ContentFormat.TEXT_POST],
    )
    assert split["formats"] == ["image", "text_post"]
    assert len(split["variants"]) == 2


def test_split_gates_every_variant():
    split = build_split("invisible illness at work", platform=Platform.INSTAGRAM)
    for v in split["variants"]:
        assert "brand_passed" in v
        assert "quality_avg" in v
        assert "needs_review" in v
    assert split["funnel"]["raw"] == len(split["variants"])


def test_persist_queues_variants_tagged_by_experiment_and_format():
    repo = get_repository()
    split = build_split("apprenticeships", persist=True,
                        formats=[ContentFormat.SHORT_VIDEO, ContentFormat.CAROUSEL])
    assert split["persisted"] is True
    assert len(split["queued_ids"]) == split["funnel"]["brand_passed"]
    queued = repo.list_queue(limit=100)
    exp_tag = f"split:{split['experiment_id']}"
    tagged = [q for q in queued if exp_tag in (q.get("tags") or [])]
    assert tagged
    # Each persisted variant also carries its format tag.
    assert any("format:short_video" in (q.get("tags") or []) for q in tagged)


def test_dry_run_does_not_touch_the_queue():
    repo = get_repository()
    before = len(repo.list_queue(limit=200))
    build_split("dry run idea")  # persist defaults to False
    assert len(repo.list_queue(limit=200)) == before


# --- the leaderboard --------------------------------------------------------


def _queue_post(repo, candidate_id: str, content_format: str) -> None:
    repo.enqueue(
        {
            "candidate_id": candidate_id,
            "candidate": {"id": candidate_id, "content_format": content_format},
            "status": "published",
        }
    )


def test_leaderboard_ranks_formats_by_average_signal():
    repo = get_repository()
    # Two formats, with carousel clearly outperforming short_video.
    _queue_post(repo, "v1", "short_video")
    _queue_post(repo, "v2", "carousel")
    for val in (10.0, 20.0, 30.0):
        repo.record_signal("v1", "tiktok", "views", val, [])
    for val in (100.0, 200.0, 300.0):
        repo.record_signal("v2", "tiktok", "views", val, [])

    board = format_leaderboard(metric="views")
    assert board["by_format"][0]["format"] == "carousel"
    assert board["recommended"] == "carousel"
    assert board["confident"] is True


def test_leaderboard_withholds_recommendation_below_min_samples():
    repo = get_repository()
    _queue_post(repo, "v1", "image")
    repo.record_signal("v1", "tiktok", "views", 50.0, [])  # only one sample
    board = format_leaderboard(metric="views", min_samples=3)
    assert board["recommended"] is None
    assert board["confident"] is False


def test_leaderboard_is_empty_with_no_signals():
    board = format_leaderboard()
    assert board["by_format"] == []
    assert board["recommended"] is None


# --- HTTP surface -----------------------------------------------------------


def test_split_api():
    r = client.post(
        "/v1/split/build",
        json={"brief": "national tradesperson day", "formats": ["image", "text_post"]},
    ).json()
    assert len(r["variants"]) == 2

    board = client.get("/v1/split/leaderboard?metric=views").json()
    assert "by_format" in board
    assert board["metric"] == "views"
