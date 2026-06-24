"""Tests for the credible-source layer and the Credible Source Rule (fact-check).

The most important behaviour: a fact-led post with no credible source is **not ok**,
and a social/community source can never back a hard fact. Everything is deterministic.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services.fact_check import (
    MAX_TIER_FOR_FACTS,
    check_post,
    credibility,
    is_fact_led,
)
from invisable_os.store import get_repository

# --- credibility hierarchy --------------------------------------------------


def test_credibility_hierarchy_ranks_gov_above_social():
    gov_tier, _ = credibility("gov")
    social_tier, _ = credibility("social")
    assert gov_tier < social_tier
    assert gov_tier == 1
    assert social_tier == 8


def test_unknown_source_type_is_midlow_tier():
    tier, _ = credibility("some-random-blog")
    assert tier == 7  # usable for facts, but only just


def test_social_sources_cannot_back_hard_facts():
    social_tier, _ = credibility("social")
    assert social_tier > MAX_TIER_FOR_FACTS


# --- fact-led detection -----------------------------------------------------


def test_percentage_makes_a_post_fact_led():
    fact_led, reasons = is_fact_led("Tool theft rose 20% last year.")
    assert fact_led is True
    assert reasons


def test_attribution_phrase_makes_a_post_fact_led():
    fact_led, _ = is_fact_led("According to the NHS, waiting lists grew.")
    assert fact_led is True


def test_pure_opinion_is_not_fact_led():
    fact_led, reasons = is_fact_led("Sending strength to anyone having a rough day in the trades.")
    assert fact_led is False
    assert reasons == []


# --- the Credible Source Rule ----------------------------------------------


def test_fact_led_with_no_source_is_not_ok():
    v = check_post("Tool theft rose 20% in 2024 according to official figures.")
    assert v.fact_led is True
    assert v.ok is False
    assert "NO source" in v.advisory or "Attach" in v.advisory


def test_fact_led_with_credible_source_is_ok_and_attributed():
    ons = {"name": "ONS", "source_type": "ons"}
    v = check_post("Tool theft rose 20%.", [ons])
    assert v.ok is True
    assert "Source: ONS" in v.attributions


def test_fact_led_with_only_social_source_is_not_ok():
    tweet = {"name": "@someone", "source_type": "social"}
    v = check_post("Tool theft rose 20%.", [tweet])
    assert v.ok is False
    assert "@someone" in v.weak_sources


def test_non_fact_led_post_is_always_ok():
    v = check_post("Be kind to yourself today.")
    assert v.fact_led is False
    assert v.ok is True


# --- store + HTTP -----------------------------------------------------------


def test_source_and_claim_round_trip():
    repo = get_repository()
    sid = repo.add_source({"name": "ONS", "source_type": "ons", "credibility_level": 2})
    repo.add_source_claim({"source_id": sid, "claim_text": "x", "confidence_score": 0.9})
    assert repo.list_sources()[0]["name"] == "ONS"
    assert len(repo.list_source_claims(source_id=sid)) == 1


def test_sources_listed_best_credibility_first():
    repo = get_repository()
    repo.add_source({"name": "Trade blog", "source_type": "trade_media", "credibility_level": 7})
    repo.add_source({"name": "Gov", "source_type": "gov", "credibility_level": 1})
    names = [s["name"] for s in repo.list_sources()]
    assert names[0] == "Gov"  # lowest credibility_level (best) first


def test_factcheck_api_end_to_end():
    client = TestClient(app)
    sid = client.post(
        "/v1/sources", json={"name": "ONS", "source_type": "ons"}
    ).json()["id"]
    # fact-led, sourced → ok
    ok = client.post(
        "/v1/factcheck", json={"text": "Tool theft rose 20%", "source_ids": [sid]}
    ).json()
    assert ok["ok"] is True
    # fact-led, unsourced → not ok
    bad = client.post(
        "/v1/factcheck", json={"text": "Tool theft rose 20% according to figures"}
    ).json()
    assert bad["ok"] is False


def test_hierarchy_endpoint_is_ordered():
    client = TestClient(app)
    tiers = [h["tier"] for h in client.get("/v1/sources/hierarchy").json()["hierarchy"]]
    assert tiers == sorted(tiers)
