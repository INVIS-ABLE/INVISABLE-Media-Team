"""Tests for the Big Campaign Button.

Hitting the button must concentrate the platform on one theme: generate a
coordinated, gated burst, surface matching reserve as reinforcements, and treat a
sensitive theme with care — never hype. Everything is deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.models.content import Platform
from invisable_os.services.campaign import CAMPAIGN_ANGLES, launch_campaign
from invisable_os.store import get_repository

client = TestClient(app)


# --- generation + gating ----------------------------------------------------


def test_campaign_generates_a_gated_burst():
    plan = launch_campaign("apprenticeships keep the trades alive", posts=8)
    assert plan["requested"] == 8
    assert plan["funnel"]["raw"] == 8
    # Brand-safe content survives the hard gate; usable count is what's ready.
    assert plan["funnel"]["usable"] >= 1
    assert plan["ready_to_queue"] == plan["funnel"]["usable"]
    assert plan["campaign_id"]


def test_campaign_spreads_across_pillars():
    plan = launch_campaign("invisible illness at work", posts=len(CAMPAIGN_ANGLES))
    pillars = {g["pillar"] for g in plan["generated"]}
    # A coordinated burst speaks in more than one voice.
    assert len(pillars) >= 2


def test_campaign_respects_the_post_ceiling():
    plan = launch_campaign("big launch", posts=999)
    assert plan["requested"] <= 60
    assert plan["funnel"]["raw"] <= 60


# --- care first -------------------------------------------------------------


def test_sensitive_campaign_is_flagged_for_care():
    plan = launch_campaign("I felt suicidal and want others to know they're not alone")
    assert plan["crisis"]["sensitive"] is True
    assert plan["crisis"]["requirements"]["approval_required"] is True


def test_ordinary_campaign_is_not_flagged():
    plan = launch_campaign("funny POV about losing tools on site", posts=4)
    assert plan["crisis"]["sensitive"] is False


# --- reinforcements ---------------------------------------------------------


def test_campaign_surfaces_matching_reserve_as_reinforcements():
    repo = get_repository()
    repo.add_war_chest_item(
        {"id": "r1", "title": "Apprenticeships save the trades", "category": "education",
         "tags": ["apprenticeships"], "reserve_status": "ready"}
    )
    repo.add_war_chest_item(
        {"id": "r2", "title": "Totally unrelated pun about tea", "category": "humour",
         "reserve_status": "ready"}
    )
    plan = launch_campaign("apprenticeships in construction", theme="apprenticeships", posts=4)
    ids = {r["id"] for r in plan["reinforcements"]}
    assert "r1" in ids
    assert "r2" not in ids


def test_used_reserve_is_not_reinforcement():
    repo = get_repository()
    repo.add_war_chest_item(
        {"id": "u1", "title": "apprenticeships piece", "reserve_status": "used",
         "tags": ["apprenticeships"]}
    )
    plan = launch_campaign("apprenticeships", theme="apprenticeships", posts=2)
    assert all(r["id"] != "u1" for r in plan["reinforcements"])


# --- persistence ------------------------------------------------------------


def test_persist_queues_campaign_tagged_drafts():
    repo = get_repository()
    plan = launch_campaign("trades mental health week", posts=6, persist=True,
                           platform=Platform.INSTAGRAM)
    assert plan["persisted"] is True
    assert len(plan["queued_ids"]) == plan["funnel"]["usable"]
    queued = repo.list_queue(limit=100)
    tag = f"campaign:{plan['campaign_id']}"
    assert any(tag in (q.get("tags") or []) for q in queued)


def test_dry_run_does_not_touch_the_queue():
    repo = get_repository()
    before = len(repo.list_queue(limit=200))
    launch_campaign("dry run theme", posts=5)  # persist defaults to False
    assert len(repo.list_queue(limit=200)) == before


# --- HTTP surface -----------------------------------------------------------


def test_campaign_api():
    r = client.post(
        "/v1/campaign/launch",
        json={"brief": "national tradesperson day", "posts": 6},
    ).json()
    assert r["requested"] == 6
    assert "funnel" in r
    assert "reinforcements" in r
