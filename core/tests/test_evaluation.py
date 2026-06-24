"""Tests for the Evaluation layer.

One scorecard across every gate: brand safety, the Credible Source Rule, mission,
quality, humanness, and crisis care. Deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services.evaluation import evaluate_batch, evaluate_post

client = TestClient(app)

_METRICS = {
    "brand_safety", "fact_grounded", "mission_aligned",
    "quality", "humanness", "crisis_care",
}


# --- the scorecard ----------------------------------------------------------


def test_scorecard_covers_every_metric():
    r = evaluate_post("On site again, pacing through a tough week. Proud of the graft.")
    assert {m["name"] for m in r["metrics"]} == _METRICS
    assert r["total"] == 6
    assert 0.0 <= r["pass_rate"] <= 1.0
    assert r["grade"] in {"A", "B", "C", "D", "F"}


def test_clean_on_mission_copy_scores_well():
    r = evaluate_post(
        "You're not invisible. Living with a condition nobody can see is real work — "
        "sending strength to every grafter pushing through today."
    )
    # Not sensitive, brand-safe, on-mission: should pass most/all metrics.
    assert r["pass_rate"] >= 0.6
    assert any(m["name"] == "crisis_care" and m["passed"] for m in r["metrics"])


# --- fact grounding ---------------------------------------------------------


def test_fact_led_without_source_fails_fact_grounded():
    r = evaluate_post("Tool theft rose 20% last year.")
    fact = next(m for m in r["metrics"] if m["name"] == "fact_grounded")
    assert fact["passed"] is False
    assert r["overall_pass"] is False


def test_fact_led_with_credible_source_passes_fact_grounded():
    r = evaluate_post(
        "Tool theft rose 20% last year.",
        sources=[{"name": "ONS", "source_type": "gov"}],
    )
    fact = next(m for m in r["metrics"] if m["name"] == "fact_grounded")
    assert fact["passed"] is True


# --- crisis care ------------------------------------------------------------


def test_sensitive_copy_flags_crisis_care_and_attaches_signposting():
    r = evaluate_post("I felt suicidal last winter and didn't tell anyone.")
    crisis = next(m for m in r["metrics"] if m["name"] == "crisis_care")
    assert crisis["passed"] is False
    assert r["sensitive"] is True
    assert any("Samaritans" in s for s in r["signposting"])


# --- humanness --------------------------------------------------------------


def test_ai_tells_drag_the_humanness_metric():
    r = evaluate_post(
        "In today's fast-paced world, we leverage cutting-edge, seamless solutions "
        "to delve into this game-changer."
    )
    human = next(m for m in r["metrics"] if m["name"] == "humanness")
    assert human["passed"] is False


# --- batch ------------------------------------------------------------------


def test_batch_reports_aggregate():
    out = evaluate_batch(
        [
            "Proud of the graft today, lads.",
            "Tool theft rose 20% last year.",  # fact-led, unsourced → fails
        ]
    )
    assert out["count"] == 2
    assert 0.0 <= out["avg_pass_rate"] <= 1.0
    assert out["grade"] in {"A", "B", "C", "D", "F"}


def test_batch_accepts_dicts_with_sources():
    out = evaluate_batch(
        [{"text": "Tool theft rose 20%.", "sources": [{"name": "ONS", "source_type": "gov"}]}]
    )
    fact = next(m for m in out["results"][0]["metrics"] if m["name"] == "fact_grounded")
    assert fact["passed"] is True


# --- HTTP surface -----------------------------------------------------------


def test_evaluate_api():
    r = client.post(
        "/v1/evaluate",
        json={"text": "You're not invisible — your work matters."},
    ).json()
    assert "metrics" in r
    assert r["total"] == 6
    assert "grade" in r
