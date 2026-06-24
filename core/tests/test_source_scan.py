"""Tests for source-led scanning — feeding the swarm topics from configured sources.

Two invariants matter most: it **degrades gracefully** (no network / no feeds → the
seed pool, never an exception), and every scanner bot is **always represented** so the
swarm never starves. All deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services.source_scan import (
    DEFAULT_UK_SOURCES,
    _route_bot,
    fetch_rss_titles,
    gather_topics,
    seed_default_sources,
)
from invisable_os.services.swarm import _SCAN_TOPICS
from invisable_os.store import get_repository

# --- routing ----------------------------------------------------------------


def test_routing_sends_sources_to_the_right_bot():
    assert _route_bot("nhs health", "nhs") == "UK Source Scanner Bot"
    assert _route_bot("construction tool theft", "construction_press") == "Construction Scanner Bot"
    assert _route_bot("chronic fatigue", "charity") == "Autoimmune & Invisible Illness Bot"


def test_routing_defaults_to_uk_source_bot():
    assert _route_bot("", "") == "UK Source Scanner Bot"


# --- graceful degradation ---------------------------------------------------


def test_fetch_rss_titles_is_offline_safe():
    # A bad/unreachable URL must yield [] rather than raising.
    assert fetch_rss_titles("not-a-url") == []
    assert fetch_rss_titles("") == []


def test_gather_topics_offline_returns_the_seed_pool():
    topics = gather_topics(_SCAN_TOPICS, live=False)
    assert set(topics) == set(_SCAN_TOPICS)
    for bot, seeds in _SCAN_TOPICS.items():
        assert topics[bot] == list(seeds)


def test_gather_topics_live_but_offline_still_feeds_every_bot():
    # With sources seeded but no network, live fetch returns nothing → seed fallback.
    seed_default_sources()
    topics = gather_topics(_SCAN_TOPICS, live=True)
    assert all(topics[bot] for bot in _SCAN_TOPICS)  # nobody starves


# --- seeding ----------------------------------------------------------------


def test_seed_default_sources_is_idempotent():
    assert seed_default_sources() == len(DEFAULT_UK_SOURCES)
    assert seed_default_sources() == 0  # already present
    names = {s["name"] for s in get_repository().list_sources()}
    assert "GOV.UK announcements" in names


# --- HTTP surface -----------------------------------------------------------


def test_swarm_topics_endpoint_previews_the_seed_pool():
    client = TestClient(app)
    body = client.get("/v1/swarm/topics?live=false").json()
    assert len(body["topics"]) == len(_SCAN_TOPICS)
    assert body["total"] == sum(len(v) for v in _SCAN_TOPICS.values())


def test_swarm_seed_sources_endpoint():
    client = TestClient(app)
    assert client.post("/v1/swarm/sources/seed").json()["added"] == len(DEFAULT_UK_SOURCES)


def test_cycle_with_live_sources_flag_runs():
    client = TestClient(app)
    r = client.post("/v1/swarm/run", json={"drafts_per_topic": 1, "live_sources": False}).json()
    assert r["funnel"]["raw_drafts"] > 0
