"""The human-led co-pilot: intensity modes, emergency controls, Interaction Centre."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.operating import (
    MODE_POLICIES,
    OperatingMode,
    clear_today_queue,
    founder_override,
    get_interaction_centre,
    get_policy,
    set_control,
    set_mode,
    today_status,
)
from invisable_os.operating.interaction import InteractionStatus

client = TestClient(app)


# --- modes: the four intensity levels ---------------------------------------


def test_four_modes_exist_with_ascending_intensity():
    assert set(MODE_POLICIES) == set(OperatingMode)
    levels = [MODE_POLICIES[m].level for m in OperatingMode]
    assert sorted(levels) == [1, 2, 3, 4]
    # Posts-per-day ceiling rises with the level.
    by_level = sorted(MODE_POLICIES.values(), key=lambda p: p.level)
    assert [p.posts_max for p in by_level] == sorted(p.posts_max for p in by_level)


@pytest.mark.parametrize("mode", list(OperatingMode))
def test_every_mode_is_human_gated(mode):
    """No mode may ever auto-act, and approval is always required — even Career."""
    p = get_policy(mode)
    assert p.approval_required is True
    assert p.auto_comments is False
    assert p.auto_dms is False
    assert p.auto_follow is False
    assert p.auto_reposts is False
    assert p.reply_mode == "draft_only"


def test_mode_volumes_match_the_brief():
    def bounds(mode):
        p = get_policy(mode)
        return (p.posts_min, p.posts_max)

    assert bounds("introduction") == (1, 3)
    assert bounds("modest_growth") == (3, 6)
    assert bounds("active_influencer") == (6, 12)
    assert bounds("career") == (12, 20)
    # Introduction has no story automation; Career has high story activity.
    assert get_policy("introduction").stories_max == 0
    assert get_policy("career").stories_max >= 10


def test_introduction_is_the_safe_default():
    assert today_status()["mode"]["key"] == "introduction"


# --- state + emergency controls ---------------------------------------------


def test_set_mode_changes_allowances():
    set_mode(OperatingMode.CAREER)
    s = today_status()
    assert s["mode"]["key"] == "career"
    assert s["posts_allowed_today"] == {"min": 12, "max": 20}


def test_stop_posting_zeroes_todays_allowance():
    set_mode(OperatingMode.ACTIVE_INFLUENCER)
    set_control("stop_posting", True)
    s = today_status()
    assert s["posting_blocked"] is True
    assert s["posts_allowed_today"] == {"min": 0, "max": 0}
    assert s["stories_allowed_today"] == {"min": 0, "max": 0}


def test_pause_all_blocks_posting_and_interactions_and_syncs_automation():
    set_control("pause_all", True)
    s = today_status()
    assert s["posting_blocked"] is True
    assert s["interactions_blocked"] is True
    # The platform-wide automation flag is flipped too.
    from invisable_os.store import get_repository

    assert get_repository().get_flag("automation").get("paused") is True


def test_unknown_control_is_rejected():
    with pytest.raises(ValueError):
        set_control("launch_nukes", True)


def test_founder_override_enables_manual_mode():
    state = founder_override(active=True, note="Stephen on stage at the expo")
    assert state["manual_mode"] is True
    assert state["founder_override"]["active"] is True
    assert today_status()["controls"]["manual_mode"] is True
    founder_override(active=False)
    assert today_status()["founder_override"]["active"] is False


def test_human_approval_is_always_required():
    for mode in OperatingMode:
        set_mode(mode)
        assert today_status()["human_approval_required"] is True


def test_clear_today_queue_removes_generated_drafts():
    from invisable_os.engines.studio import StudioEngine
    from invisable_os.studio import get_studio_store

    get_studio_store().save_batch(StudioEngine().generate_batch("humour", count=2))
    assert get_studio_store().stats()["generated"] == 2
    assert clear_today_queue()["cleared"] == 2
    assert get_studio_store().stats()["generated"] == 0


# --- Interaction Centre -----------------------------------------------------


def test_interaction_seed_and_draft_then_send():
    centre = get_interaction_centre()
    centre.seed_demo()
    items = centre.list_items()
    assert len(items) >= 6
    # Urgent items sort first.
    assert items[0].priority in ("urgent", "high")

    drafted = centre.draft_reply(items[0].id)
    assert drafted.status == InteractionStatus.DRAFTED
    assert drafted.suggested_reply
    assert drafted.reply_approved is True  # compliant by construction

    sent = centre.mark_sent(items[0].id)
    assert sent.status == InteractionStatus.SENT


def test_interaction_dismiss_and_edit():
    centre = get_interaction_centre()
    centre.seed_demo()
    item = centre.list_items()[0]
    edited = centre.edit_reply(item.id, "Thank you so much for sharing this with us.")
    assert edited.suggested_reply.startswith("Thank you")
    assert centre.dismiss(item.id).status == InteractionStatus.DISMISSED


def test_drafted_reply_is_guardrail_clean():
    centre = get_interaction_centre()
    centre.seed_demo()
    for item in centre.list_items():
        drafted = centre.draft_reply(item.id)
        # No hearts/kisses, no engagement bait — enforced by the shared guardrails.
        assert "❤" not in drafted.suggested_reply
        assert "follow me" not in drafted.suggested_reply.lower()


# --- API surface ------------------------------------------------------------


def test_api_operating_modes_lists_four_levels_and_rules():
    data = client.get("/v1/operating/modes").json()
    assert len(data["modes"]) == 4
    assert "Auto-DM people" in data["human_rules"]["never"]
    assert "Heart emojis" in data["comment_style"]["avoid"]


def test_api_set_mode_and_status():
    r = client.post("/v1/operating/mode", json={"mode": "career"}).json()
    assert r["ok"] is True
    assert r["status"]["mode"]["key"] == "career"
    assert r["status"]["human_approval_required"] is True


def test_api_bad_mode_returns_error():
    assert "error" in client.post("/v1/operating/mode", json={"mode": "nope"}).json()


def test_api_controls_and_founder_override():
    r = client.post("/v1/operating/control", json={"control": "stop_posting", "value": True}).json()
    assert r["status"]["posting_blocked"] is True
    fo = client.post("/v1/operating/founder-override", json={"active": True}).json()
    assert fo["status"]["controls"]["manual_mode"] is True


def test_api_interaction_flow():
    seeded = client.post("/v1/interaction/seed").json()
    assert seeded["seeded"] >= 6
    listed = client.get("/v1/interaction").json()
    assert listed["counts"]["needs_attention"] >= 6
    pid = listed["items"][0]["id"]
    drafted = client.post(f"/v1/interaction/{pid}/draft").json()
    assert drafted["item"]["suggested_reply"]
    sent = client.post(f"/v1/interaction/{pid}/sent").json()
    assert sent["item"]["status"] == "sent"


def test_api_clear_today():
    r = client.post("/v1/operating/clear-today").json()
    assert r["ok"] is True
    assert "cleared" in r
