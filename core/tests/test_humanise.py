"""Tests for the Humanisation layer.

Generated copy has tells; this layer flags and strips them without changing
meaning. Deterministic and offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services.humanise import humanise, humanness_score

client = TestClient(app)


# --- scoring ----------------------------------------------------------------


def test_clean_human_copy_scores_high():
    s = humanness_score("Long shift today. Knackered, but the job's done and I'm proud of it.")
    assert s["score"] >= 0.8
    assert s["human"] is True
    assert s["tell_count"] == 0


def test_ai_cliches_are_flagged():
    s = humanness_score(
        "In today's fast-paced world, we leverage cutting-edge tools to delve into "
        "this game-changer. Furthermore, it's important to note that it's seamless."
    )
    assert s["tell_count"] >= 4
    assert s["score"] < 0.8
    assert s["by_kind"].get("cliche", 0) >= 4


def test_emoji_spam_is_flagged():
    s = humanness_score("Big news 🎉🎉🔥🔥💪💯 check it out")
    assert s["by_kind"].get("emoji_spam", 0) == 1


def test_em_dash_overuse_is_flagged():
    s = humanness_score("This — that — and the other — all at once — endlessly.")
    assert s["by_kind"].get("em_dash_overuse", 0) == 1


# --- humanising -------------------------------------------------------------


def test_humanise_removes_cliches_and_improves_the_score():
    result = humanise(
        "Furthermore, we leverage cutting-edge tools to delve into this game-changer."
    )
    low = result["humanised"].lower()
    assert "leverage" not in low
    assert "cutting-edge" not in low
    assert "delve" not in low
    assert "game-changer" not in low
    assert result["score_after"] > result["score_before"]
    assert result["removed"] >= 3


def test_humanise_collapses_em_dashes():
    result = humanise("On site — again — today.")
    assert "—" not in result["humanised"]


def test_humanise_is_idempotent_on_clean_copy():
    clean = "Tools nicked off the van again. Gutted. Lock everything, lads."
    result = humanise(clean)
    assert result["humanised"] == clean
    assert result["removed"] == 0


def test_humanise_recapitalises_after_a_leading_cliche_is_removed():
    # "In conclusion, " is deleted; the next word should start the sentence capitalised.
    result = humanise("In conclusion, the work speaks for itself.")
    assert result["humanised"].startswith("The work")


# --- HTTP surface -----------------------------------------------------------


def test_humanise_api():
    r = client.post(
        "/v1/humanise",
        json={"text": "Furthermore, we utilise robust, seamless, cutting-edge solutions."},
    ).json()
    assert "utilise" not in r["humanised"].lower()
    assert r["score_after"] >= r["score_before"]
