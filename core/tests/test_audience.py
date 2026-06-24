"""Tests for Audience Command — personas, voice bank, and the Hook Laboratory.

All deterministic and offline: registries are fixed, targeting and scoring are
keyword/shape based, and the Hook Lab degrades to on-brand templates with no model.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.engines.audience import (
    PERSONAS,
    VOICE_BANK,
    AudiencePersona,
    VoiceMode,
    pick_voice,
    target_persona,
)
from invisable_os.engines.hooks import HOOK_TYPES, SCORE_AXES, HookLab, score_hook
from invisable_os.main import app

client = TestClient(app)


# --- personas ---------------------------------------------------------------


def test_eight_personas_with_unique_ids():
    assert len(PERSONAS) == 8
    ids = [p.id for p in PERSONAS]
    assert len(ids) == len(set(ids))
    assert set(ids) == set(AudiencePersona)


def test_targeting_picks_the_right_primary_persona():
    assert target_persona("grafting on site with a flare and chronic fatigue").persona == (
        AudiencePersona.TRADES_INVISIBLE_ILLNESS
    )
    assert target_persona("CT1 sponsor brand partnership campaign").persona == (
        AudiencePersona.SPONSOR_PARTNER
    )
    assert target_persona("my partner has it and I want to help as their carer").persona == (
        AudiencePersona.FAMILY_CARER
    )


def test_targeting_always_returns_a_primary_even_with_no_signal():
    # There is always a primary persona — unmatched text falls back to general public.
    m = target_persona("what a lovely afternoon")
    assert m.persona == AudiencePersona.GENERAL_PUBLIC


def test_platform_fit_nudges_score():
    m = target_persona("chronic fatigue on site", platform="tiktok")
    assert m.score > 0


# --- voice bank -------------------------------------------------------------


def test_nine_voice_modes():
    assert len(VOICE_BANK) == 9
    assert {v.id for v in VOICE_BANK} == set(VoiceMode)


def test_pick_voice_defaults_and_overrides():
    assert pick_voice(pillar="founder").id == VoiceMode.STEPHEN_RAW
    assert pick_voice(pillar="partner").id == VoiceMode.SPONSOR_SAFE
    # A sponsor/partner persona forces the sponsor-safe voice regardless of pillar.
    assert pick_voice(pillar="humour", persona="sponsor_partner").id == VoiceMode.SPONSOR_SAFE
    # Unknown pillar → the dependable official voice.
    assert pick_voice(pillar="nonsense").id == VoiceMode.INVISABLE_OFFICIAL


# --- hook laboratory --------------------------------------------------------


def test_hook_lab_produces_ten_scored_hooks_best_first():
    result = HookLab().run("tool theft from vans", platform="tiktok")
    assert len(result.hooks) == len(HOOK_TYPES) == 10
    totals = [h.total for h in result.hooks]
    assert totals == sorted(totals, reverse=True)
    assert result.best is result.hooks[0]
    # Every hook is scored on all six axes.
    assert set(result.best.scores) == set(SCORE_AXES)


def test_hook_types_are_all_distinct():
    types = [h.hook_type for h in HookLab().run("chronic illness").hooks]
    assert len(types) == len(set(types)) == 10


def test_score_hook_rewards_curiosity_and_brevity():
    strong = score_hook("Nobody talks about the truth about invisible illness", "nobody_talks")
    weak = score_hook(
        "Here is a fairly ordinary and very long sentence that simply keeps going well past "
        "any reasonable hook length without a single curiosity word in it at all",
        "question",
    )
    assert strong.total > weak.total


# --- HTTP surface -----------------------------------------------------------


def test_audience_api_round_trip():
    assert len(client.get("/v1/personas").json()["personas"]) == 8
    assert len(client.get("/v1/voices").json()["voices"]) == 9
    assert len(client.get("/v1/hooks/types").json()["hook_types"]) == 10

    target = client.post(
        "/v1/personas/target", json={"text": "self-employed builder, no sick pay, van theft"}
    ).json()
    assert target["persona"] == "self_employed_builder"

    lab = client.post(
        "/v1/hooks/lab",
        json={
            "topic": "fatigue on site",
            "platform": "tiktok",
            "persona": "trades_invisible_illness",
        },
    ).json()
    assert len(lab["hooks"]) == 10
    assert lab["best"]["total"] >= lab["hooks"][-1]["total"]
