"""Tests for the Content War Chest — the reserve that lets the platform post at scale.

Covers stocking (idempotent), reserve-health tiers + recommended cadence, freshness,
and anti-repetition selection that rotates categories. All deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.models.content import QueueStatus
from invisable_os.services import reserve_health, select_next, stock_approved
from invisable_os.services.war_chest import RESERVE_HEALTHY, reserve_tier
from invisable_os.store import get_repository


def _approve(repo, *, pillar="humour", platform="tiktok", quality=8.0, mission=0.6, hook="h"):
    item_id = repo.enqueue(
        {
            "candidate": {"hook": hook, "scores": {"humour": 0.5}},
            "pillar": pillar,
            "platform": platform,
            "quality_avg": quality,
            "mission_total": mission,
            "tags": ["@x"],
        }
    )
    repo.transition(item_id, QueueStatus.APPROVED)
    return item_id


# --- reserve tiers ----------------------------------------------------------


def test_reserve_tiers_match_spec_thresholds():
    assert reserve_tier(0) == "below_minimum"
    assert reserve_tier(499) == "below_minimum"
    assert reserve_tier(500) == "minimum"
    assert reserve_tier(1_000) == "healthy"
    assert reserve_tier(2_000) == "elite"
    assert reserve_tier(5_000) == "elite"


# --- stocking ---------------------------------------------------------------


def test_stock_approved_moves_approved_items_into_reserve():
    repo = get_repository()
    for i in range(3):
        _approve(repo, hook=f"h{i}")
    result = stock_approved()
    assert result["stocked"] == 3
    assert result["counts"]["ready"] == 3


def test_stocking_is_idempotent():
    repo = get_repository()
    _approve(repo)
    assert stock_approved()["stocked"] == 1
    assert stock_approved()["stocked"] == 0  # already stocked → not duplicated
    assert reserve_health()["ready"] == 1


def test_evergreen_pillars_marked_evergreen():
    repo = get_repository()
    _approve(repo, pillar="education")
    _approve(repo, pillar="trends")
    stock_approved()
    items = {i["pillar"]: i for i in repo.list_war_chest()}
    assert items["education"]["evergreen"] is True
    assert items["trends"]["evergreen"] is False


# --- reserve health ---------------------------------------------------------


def test_reserve_health_reports_tier_and_cadence():
    repo = get_repository()
    _approve(repo)
    stock_approved()
    h = reserve_health()
    assert h["tier"] == "below_minimum"
    assert h["recommended_posts_per_day"] == 24  # protect a thin reserve
    assert h["recommended_interval_minutes"] == 60
    assert h["thresholds"]["healthy"] == RESERVE_HEALTHY


def test_reserve_health_category_spread():
    repo = get_repository()
    _approve(repo, pillar="humour")
    _approve(repo, pillar="education")
    stock_approved()
    cats = reserve_health()["by_category"]
    assert cats.get("humour") == 1
    assert cats.get("education") == 1


# --- selection (anti-repetition) -------------------------------------------


def test_select_next_rotates_categories():
    repo = get_repository()
    for p in ("humour", "education", "founder", "community"):
        _approve(repo, pillar=p)
    stock_approved()
    first = select_next()
    second = select_next()
    assert first["item"]["category"] != second["item"]["category"]
    assert second["rotated_from_category"] == first["item"]["category"]


def test_select_next_marks_item_used_and_decrements_ready():
    repo = get_repository()
    _approve(repo)
    stock_approved()
    assert reserve_health()["ready"] == 1
    chosen = select_next()
    assert "item" in chosen
    assert reserve_health()["ready"] == 0
    assert repo.war_chest_counts()["by_status"].get("used") == 1


def test_select_next_empty_reserve_returns_error():
    assert "error" in select_next()


def test_select_prefers_higher_quality():
    repo = get_repository()
    _approve(repo, pillar="humour", quality=4.0, hook="low")
    _approve(repo, pillar="humour", quality=9.0, hook="high")
    stock_approved()
    chosen = select_next()
    assert chosen["item"]["payload"]["hook"] == "high"


# --- HTTP surface -----------------------------------------------------------


def test_warchest_api_round_trip():
    client = TestClient(app)
    repo = get_repository()
    for p in ("humour", "education", "founder"):
        _approve(repo, pillar=p)
    assert client.post("/v1/warchest/stock").json()["stocked"] == 3
    health = client.get("/v1/warchest").json()
    assert health["ready"] == 3
    assert health["tier"] == "below_minimum"
    assert len(client.get("/v1/warchest/items").json()["items"]) == 3
    selected = client.post("/v1/warchest/select", json={}).json()
    assert "item" in selected
