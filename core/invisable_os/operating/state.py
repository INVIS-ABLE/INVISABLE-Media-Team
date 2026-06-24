"""Operating state — the live mode, emergency controls, and the daily snapshot.

This is the co-pilot's control panel state: which intensity mode is active, which
emergency controls Stephen has pulled, and the single status snapshot the app shows
(posts allowed today, stories allowed today, pending approvals, pending interactions,
recommended actions, risk level, and — always — that human approval is required).

State is persisted via the same ``system_flag`` store the automation switches already
use, so the desktop apps and the engines read one consistent picture. Pulling an
emergency control here also flips the existing automation/posting flags so the rest
of the platform honours it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from invisable_os.operating.interaction import get_interaction_centre
from invisable_os.operating.modes import (
    DEFAULT_MODE,
    GLOBAL_HUMAN_RULES,
    OperatingMode,
    get_policy,
)
from invisable_os.store import get_repository

_FLAG_KEY = "operating"

# The emergency controls, mapped to what they do.
CONTROLS = ("pause_all", "manual_mode", "stop_posting", "stop_interactions")


def _default_state() -> dict:
    return {
        "mode": DEFAULT_MODE.value,
        "pause_all": False,
        "manual_mode": False,
        "stop_posting": False,
        "stop_interactions": False,
        "founder_override": {"active": False, "note": "", "at": ""},
    }


def _load() -> dict:
    state = get_repository().get_flag(_FLAG_KEY, _default_state())
    # Backfill any missing keys so older flags stay valid.
    base = _default_state()
    base.update(state)
    return base


def _save(state: dict) -> dict:
    get_repository().set_flag(_FLAG_KEY, state)
    return state


def get_state() -> dict:
    return _load()


def set_mode(mode: OperatingMode | str) -> dict:
    """Switch the intensity level. Validates against the known modes."""
    state = _load()
    state["mode"] = OperatingMode(mode).value
    return _save(state)


def _sync_automation_flags(state: dict) -> None:
    """Reflect emergency controls into the platform-wide automation switches."""
    repo = get_repository()
    posting_paused = bool(state["pause_all"] or state["stop_posting"])
    repo.set_flag(
        "posting",
        {"paused": posting_paused, "reason": "operating control" if posting_paused else ""},
    )
    repo.set_flag(
        "automation",
        {"paused": bool(state["pause_all"]), "reason": "pause_all" if state["pause_all"] else ""},
    )


def set_control(control: str, value: bool) -> dict:
    """Set one emergency control (Pause All / Manual Mode / Stop Posting / Stop Interactions)."""
    if control not in CONTROLS:
        raise ValueError(f"Unknown control: {control!r}")
    state = _load()
    state[control] = bool(value)
    _sync_automation_flags(state)
    return _save(state)


def founder_override(active: bool = True, note: str = "") -> dict:
    """Stephen takes the wheel: pause proactive AI, hand full control to the human.

    Founder Override is the big red button that asserts human authority — it switches
    on Manual Mode (the AI only drafts on request, never prepares batches or proactive
    suggestions) and records that the founder is in direct control.
    """
    state = _load()
    state["founder_override"] = {
        "active": bool(active),
        "note": note,
        "at": datetime.now(UTC).isoformat(timespec="seconds") if active else "",
    }
    state["manual_mode"] = bool(active)
    _sync_automation_flags(state)
    return _save(state)


def clear_today_queue() -> dict:
    """Clear today's generated drafts (the studio 'generated' folder)."""
    from invisable_os.studio import get_studio_store

    removed = get_studio_store().clear_status("generated")
    return {"cleared": removed}


def _pending_approvals() -> int:
    """Drafts awaiting Stephen's approval: studio drafts + queued posts pending review."""
    from invisable_os.models.content import QueueStatus
    from invisable_os.studio import get_studio_store

    studio = get_studio_store().stats().get("generated", 0)
    try:
        queued = get_repository().counts_by_status().get(QueueStatus.PENDING_REVIEW.value, 0)
    except Exception:  # noqa: BLE001 — never let a status read break the snapshot
        queued = 0
    return studio + queued


def _recommended_actions(state: dict, policy, approvals: int, interactions: int) -> list[dict]:
    """What the co-pilot suggests Stephen do next — never does on its own."""
    def act(action: str, detail: str) -> dict:
        return {"action": action, "detail": detail}

    actions: list[dict] = []
    if state["pause_all"]:
        return [act("Resume when ready", "Everything is paused. Stephen is in full control.")]
    if state["founder_override"]["active"]:
        actions.append(act(
            "Founder Override is on",
            "AI drafts on request only. Turn it off to resume co-pilot support.",
        ))
    if interactions:
        actions.append(act(
            "Review the Interaction Centre",
            f"{interactions} interaction(s) need a reply or a decision.",
        ))
    if approvals:
        actions.append(
            act("Approve or edit drafts", f"{approvals} draft(s) awaiting your approval.")
        )
    elif not state["stop_posting"]:
        actions.append(act(
            "Generate today's drafts",
            f"Mode allows {policy.posts_min}–{policy.posts_max} posts today — none prepared yet.",
        ))
    if policy.recommend_trend_reactions:
        actions.append(act(
            "Check trend reactions", "A timely, on-mission trend reaction could land well today.",
        ))
    if policy.creator_collab_suggestions:
        actions.append(act(
            "Review creator collaborations",
            "Consider creators worth amplifying or collaborating with.",
        ))
    return actions


def today_status() -> dict:
    """The single snapshot the Co-Pilot panel renders."""
    state = _load()
    policy = get_policy(state["mode"])
    posting_blocked = bool(state["pause_all"] or state["stop_posting"])
    interactions_blocked = bool(state["pause_all"] or state["stop_interactions"])

    zero = {"min": 0, "max": 0}
    posts = zero if posting_blocked else {"min": policy.posts_min, "max": policy.posts_max}
    stories = zero if posting_blocked else {"min": policy.stories_min, "max": policy.stories_max}

    approvals = _pending_approvals()
    interactions = (
        0 if interactions_blocked else get_interaction_centre().counts()["needs_attention"]
    )
    recommended = _recommended_actions(state, policy, approvals, interactions)

    return {
        "mode": policy.summary(),
        "controls": {c: state[c] for c in CONTROLS},
        "founder_override": state["founder_override"],
        "posting_blocked": posting_blocked,
        "interactions_blocked": interactions_blocked,
        "posts_allowed_today": posts,
        "stories_allowed_today": stories,
        "pending_approvals": approvals,
        "pending_interactions": interactions,
        "recommended_actions": recommended,
        "risk_level": policy.risk_level,
        "human_approval_required": True,  # always — at every level
        "human_rules": GLOBAL_HUMAN_RULES,
    }
