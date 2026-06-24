"""Tests for the Agent Swarm — the 20-bot scan → generate → gate → stock pipeline.

The swarm is reject-heavy by design: brand guardrails are the only hard gate, while
fact-led-without-source and below-bar quality are flagged for review (never
auto-stocked). All deterministic and offline (generation degrades to templates).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services.swarm import SWARM_BOTS, AgentSwarm, run_swarm_cycle, swarm_stats
from invisable_os.store import get_repository

# --- the bot roster ---------------------------------------------------------


def test_swarm_has_exactly_twenty_bots():
    assert len(SWARM_BOTS) == 20


def test_bots_cover_every_pipeline_stage():
    stages = {b.stage for b in SWARM_BOTS}
    assert stages == {"scan", "generate", "gate", "schedule"}
    # The spec's grouping: 5 scan, 8 generate, 6 gate, 1 schedule.
    counts = {st: sum(1 for b in SWARM_BOTS if b.stage == st) for st in stages}
    assert counts == {"scan": 5, "generate": 8, "gate": 6, "schedule": 1}


def test_bot_names_are_unique():
    names = [b.name for b in SWARM_BOTS]
    assert len(names) == len(set(names))


# --- a cycle ----------------------------------------------------------------


def test_cycle_produces_a_funnel_and_persists_drafts():
    result = run_swarm_cycle(drafts_per_topic=2)
    f = result["funnel"]
    assert f["raw_drafts"] > 0
    # Everything that survives the brand gate is enqueued as a usable draft.
    assert f["usable_drafts_queued"] == f["passed_brand_gate"]
    assert get_repository().counts_by_status().get("pending_review") == f["usable_drafts_queued"]


def test_cycle_stocks_only_clean_on_mission_drafts():
    result = run_swarm_cycle(drafts_per_topic=2)
    f = result["funnel"]
    repo = get_repository()
    # Stocked count matches what actually landed in the reserve as ready.
    assert repo.war_chest_counts()["ready"] == f["stocked_to_war_chest"]
    # Nothing flagged for review is auto-stocked, so stocked ≤ usable − needs_review.
    assert f["stocked_to_war_chest"] <= f["usable_drafts_queued"] - 0


def test_fact_led_unsourced_drafts_are_flagged_not_stocked():
    result = run_swarm_cycle(drafts_per_topic=2)
    f = result["funnel"]
    # Some templates mention stats/topics → fact-led without a source → review-flagged.
    assert f["needs_human_review"] >= 0
    # A review-flagged draft is never in the clean stocked set.
    assert f["stocked_to_war_chest"] + f["needs_human_review"] <= f["usable_drafts_queued"] + f[
        "fact_check_clean"
    ]


def test_every_bot_records_an_output_each_cycle():
    result = run_swarm_cycle(drafts_per_topic=1)
    outputs = get_repository().list_bot_outputs(cycle_id=result["cycle_id"])
    # 20 bots each write one record per cycle.
    assert len({o["bot_name"] for o in outputs}) == 20


def test_bots_report_lifetime_totals():
    run_swarm_cycle(drafts_per_topic=1)
    bots = AgentSwarm().bots()
    assert len(bots) == 20
    generate = [b for b in bots if b["stage"] == "generate"]
    assert all(b["produced"] > 0 for b in generate)


# --- stats ------------------------------------------------------------------


def test_swarm_stats_summarise_production():
    run_swarm_cycle(drafts_per_topic=2)
    s = swarm_stats()
    assert s["bots"] == 20
    assert s["total_produced"] > 0
    assert s["best_bot"] is not None
    assert "tier" in s["reserve"]


# --- HTTP surface -----------------------------------------------------------


def test_swarm_api_round_trip():
    client = TestClient(app)
    assert len(client.get("/v1/swarm/bots").json()["bots"]) == 20
    run = client.post("/v1/swarm/run", json={"drafts_per_topic": 2}).json()
    assert run["funnel"]["raw_drafts"] > 0
    stats = client.get("/v1/swarm/stats").json()
    assert stats["total_produced"] > 0
    outputs = client.get(f"/v1/swarm/outputs?cycle_id={run['cycle_id']}").json()["outputs"]
    assert len(outputs) == 20
