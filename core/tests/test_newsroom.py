"""Tests for Newsroom Mode.

Speed without shortcuts: a breaking item becomes a spread of gated angles, each
grounded in the supplied source. A fact-led angle with no credible source is held,
not shipped; a sensitive headline is routed through Crisis Mode. Deterministic and
offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.models.content import Platform
from invisable_os.services.newsroom import NEWSROOM_ANGLES, newsroom_brief
from invisable_os.store import get_repository

client = TestClient(app)


# --- the spread -------------------------------------------------------------


def test_newsroom_drafts_the_requested_number_of_gated_angles():
    pkg = newsroom_brief("Apprenticeship starts rise across UK construction", count=4)
    assert len(pkg["angles"]) == 4
    for a in pkg["angles"]:
        assert "brand_passed" in a
        assert "quality_avg" in a
        assert "needs_review" in a
    assert pkg["funnel"]["raw"] == 4
    assert pkg["newsroom_id"]


def test_newsroom_spreads_across_angles():
    pkg = newsroom_brief("New sick-pay guidance published", count=len(NEWSROOM_ANGLES))
    angles = {a["angle"] for a in pkg["angles"]}
    assert len(angles) >= 2


def test_newsroom_clamps_angle_count():
    pkg = newsroom_brief("big story", count=999)
    assert len(pkg["angles"]) <= 12


# --- source assessment ------------------------------------------------------


def test_credible_source_is_strong_enough_for_facts():
    pkg = newsroom_brief(
        "ONS reports tool theft up 20%",
        source_name="ONS", source_type="gov",
    )
    assert pkg["source"]["tier"] == 1
    assert pkg["source"]["credible_for_facts"] is True


def test_weak_source_is_flagged_too_weak():
    pkg = newsroom_brief(
        "Someone on X claims tool theft doubled",
        source_name="An X post", source_type="social",
    )
    assert pkg["source"]["credible_for_facts"] is False
    assert any("too weak" in g for g in pkg["guidance"])


# --- care first -------------------------------------------------------------


def test_sensitive_headline_is_not_publish_ready():
    pkg = newsroom_brief("Tradesperson suicide rates climb, new figures show",
                         source_name="ONS", source_type="gov")
    assert pkg["crisis"]["sensitive"] is True
    assert pkg["publish_ready"] is False
    assert any("Sensitive topic" in g for g in pkg["guidance"])


def test_source_required_field_is_present_and_boolean():
    pkg = newsroom_brief("Construction output figures released")  # no source supplied
    assert isinstance(pkg["source_required"], bool)
    assert isinstance(pkg["publish_ready"], bool)


# --- persistence ------------------------------------------------------------


def test_persist_queues_newsroom_tagged_drafts():
    repo = get_repository()
    pkg = newsroom_brief(
        "Apprenticeship funding boost announced",
        source_name="GOV.UK", source_type="gov",
        persist=True, platform=Platform.INSTAGRAM,
    )
    assert pkg["persisted"] is True
    assert len(pkg["queued_ids"]) == pkg["funnel"]["brand_passed"]
    queued = repo.list_queue(limit=100)
    tag = f"newsroom:{pkg['newsroom_id']}"
    assert any(tag in (q.get("tags") or []) for q in queued)


def test_dry_run_does_not_touch_the_queue():
    repo = get_repository()
    before = len(repo.list_queue(limit=200))
    newsroom_brief("a quiet news day")  # persist defaults to False
    assert len(repo.list_queue(limit=200)) == before


# --- HTTP surface -----------------------------------------------------------


def test_newsroom_api():
    r = client.post(
        "/v1/newsroom/brief",
        json={"headline": "New PIP assessment rules published",
              "source_name": "GOV.UK", "source_type": "gov", "count": 3},
    ).json()
    assert len(r["angles"]) == 3
    assert r["source"]["credible_for_facts"] is True
    assert "guidance" in r
