"""Platform Compliance Watchdog — the desktop's Platform Health surface.

These ``/api/compliance/*`` routes expose the Watchdog ([`engines.watchdog`]) to the
Studio app: the live health report, the event feed integrations write to, manual mode
control, and the emergency buttons. The Watchdog only ever *analyses and pauses* — no
route here performs or bypasses any platform action.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from invisable_os.api.desktop_routes import require_token
from invisable_os.engines.watchdog import (
    ENGAGEMENT_DROP,
    REACH_COLLAPSE,
    ActivitySnapshot,
    ComplianceWatchdog,
    PostingMode,
)
from invisable_os.models.content import QueueStatus
from invisable_os.store import get_repository

compliance_router = APIRouter(prefix="/api/compliance", tags=["compliance"])


# --- snapshot assembly ------------------------------------------------------


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def current_mode(repo) -> PostingMode:
    raw = repo.get_flag("posting_mode", {}).get("mode")
    try:
        return PostingMode(raw) if raw else PostingMode.INTRODUCTION
    except ValueError:
        return PostingMode.INTRODUCTION


def build_snapshot(repo) -> ActivitySnapshot:
    """Assemble everything the Watchdog needs from the live store."""
    today = _today_iso()
    published = repo.list_queue(QueueStatus.PUBLISHED.value, limit=500)
    posts_today = sum(1 for p in published if (p.get("published_at") or "")[:10] == today)

    events = repo.list_compliance_events(
        since=datetime.now(UTC) - timedelta(days=7), limit=200
    )

    counters = repo.get_flag("daily_counters", {})
    trends = repo.get_flag("trends", {})
    reach = float(trends.get("reach", 0.0) or 0.0)
    engagement = float(trends.get("engagement", 0.0) or 0.0)
    # Bridge explicit drop events into the trends so they register even with no
    # metrics pipeline configured.
    kinds = {e.get("kind") for e in events}
    if "reach_drop" in kinds:
        reach = min(reach, REACH_COLLAPSE)
    if "engagement_drop" in kinds:
        engagement = min(engagement, ENGAGEMENT_DROP)

    return ActivitySnapshot(
        current_mode=current_mode(repo),
        posts_today=posts_today,
        comments_today=int(counters.get("comments", 0) or 0),
        story_pushes_today=int(counters.get("story_pushes", 0) or 0),
        recent_posts=repo.list_queue(limit=40),
        events=events,
        reach_trend=reach,
        engagement_trend=engagement,
    )


def build_report(repo) -> dict:
    """Run the Watchdog over the live snapshot and return its summary + context."""
    snap = build_snapshot(repo)
    report = ComplianceWatchdog().evaluate(snap)
    summary = report.summary()
    summary.update(
        {
            "posts_today": snap.posts_today,
            "comments_today": snap.comments_today,
            "story_pushes_today": snap.story_pushes_today,
            "reach_trend": round(snap.reach_trend, 3),
            "engagement_trend": round(snap.engagement_trend, 3),
            "switches": repo.get_flag("compliance", {}),
        }
    )
    return summary


# --- routes -----------------------------------------------------------------


@compliance_router.get("/health", dependencies=[Depends(require_token)])
def api_compliance_health() -> dict:
    """The Platform Health page's main payload (read-only — does not change mode)."""
    return build_report(get_repository())


@compliance_router.post("/evaluate", dependencies=[Depends(require_token)])
def api_compliance_evaluate() -> dict:
    """Evaluate and *enforce*: auto-downgrade the mode and pause automation when the
    risk warrants it. This is the Watchdog acting on its core rule — safety wins."""
    repo = get_repository()
    snap = build_snapshot(repo)
    report = ComplianceWatchdog().evaluate(snap)

    enforced = []
    if report.suggested_mode != report.mode:
        repo.set_flag("posting_mode", {"mode": report.suggested_mode.value})
        enforced.append(f"mode → {report.suggested_mode.value}")
    if report.risk_level.value in ("high", "critical"):
        repo.set_flag(
            "automation", {"paused": True, "reason": f"watchdog:{report.risk_level.value}"}
        )
        enforced.append("automation paused")
    if report.risk_level.value == "critical":
        repo.set_flag("posting", {"paused": True, "reason": "watchdog:critical"})
        enforced.append("posting stopped")

    out = build_report(repo)
    out["enforced"] = enforced
    return out


@compliance_router.get("/events", dependencies=[Depends(require_token)])
def api_compliance_events(days: int = 7, limit: int = 100) -> dict:
    repo = get_repository()
    since = datetime.now(UTC) - timedelta(days=max(1, days))
    return {"events": repo.list_compliance_events(since=since, limit=limit)}


class ComplianceEventIn(BaseModel):
    kind: str
    platform: str = ""
    severity: str = "medium"
    detail: str = ""
    source: str = ""


@compliance_router.post("/events", dependencies=[Depends(require_token)])
def api_compliance_record_event(req: ComplianceEventIn) -> dict:
    """Integrations (Postiz/n8n/metrics) and the operator report safety events here."""
    event = get_repository().record_compliance_event(
        req.kind,
        platform=req.platform,
        severity=req.severity,
        detail=req.detail,
        source=req.source,
    )
    return {"ok": True, "event": event}


class ModeRequest(BaseModel):
    mode: str


@compliance_router.post("/mode", dependencies=[Depends(require_token)])
def api_compliance_set_mode(req: ModeRequest) -> dict:
    """Manually set the posting mode (Stephen stays in control)."""
    try:
        mode = PostingMode(req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"unknown mode '{req.mode}'") from exc
    get_repository().set_flag("posting_mode", {"mode": mode.value})
    return {"ok": True, "mode": mode.value, "report": build_report(get_repository())}


class EmergencyRequest(BaseModel):
    action: str = Field(
        description="pause_all | manual_only | stop_comments | stop_reposts | "
        "stop_story_pushes | stop_scheduling | clear_today_queue | account_cooldown"
    )


@compliance_router.post("/emergency", dependencies=[Depends(require_token)])
def api_compliance_emergency(req: EmergencyRequest) -> dict:
    """The emergency buttons. Every one only *stops* things — never starts or bypasses."""
    repo = get_repository()
    switches = dict(repo.get_flag("compliance", {}))
    action = req.action
    result: dict = {"ok": True, "action": action}

    if action == "pause_all":
        repo.set_flag("automation", {"paused": True, "reason": "emergency"})
    elif action == "manual_only":
        repo.set_flag("posting_mode", {"mode": PostingMode.MANUAL_ONLY.value})
        switches["manual_only"] = True
        repo.set_flag("compliance", switches)
    elif action == "stop_comments":
        switches["comments_stopped"] = True
        repo.set_flag("compliance", switches)
    elif action == "stop_reposts":
        switches["reposts_stopped"] = True
        repo.set_flag("compliance", switches)
    elif action == "stop_story_pushes":
        switches["story_pushes_stopped"] = True
        repo.set_flag("compliance", switches)
    elif action == "stop_scheduling":
        switches["scheduling_stopped"] = True
        repo.set_flag("compliance", switches)
    elif action == "clear_today_queue":
        result["cleared"] = _clear_today_queue(repo)
    elif action == "account_cooldown":
        repo.set_flag("posting_mode", {"mode": PostingMode.MANUAL_ONLY.value})
        repo.set_flag("automation", {"paused": True, "reason": "cooldown"})
        repo.set_flag("posting", {"paused": True, "reason": "cooldown"})
        switches["cooldown"] = True
        repo.set_flag("compliance", switches)
    else:
        raise HTTPException(status_code=422, detail=f"unknown action '{action}'")

    result["report"] = build_report(repo)
    return result


class ResetRequest(BaseModel):
    switch: str  # one of the compliance switches, or "all"


@compliance_router.post("/reset", dependencies=[Depends(require_token)])
def api_compliance_reset(req: ResetRequest) -> dict:
    """Lift an emergency switch once it's safe (the operator's call)."""
    repo = get_repository()
    if req.switch == "all":
        repo.set_flag("compliance", {})
    else:
        switches = dict(repo.get_flag("compliance", {}))
        switches[req.switch] = False
        repo.set_flag("compliance", switches)
    return {"ok": True, "report": build_report(repo)}


def _clear_today_queue(repo) -> int:
    """Reject today's not-yet-published posts — the safest 'clear' (nothing deleted)."""
    today = _today_iso()
    live = {
        QueueStatus.PENDING_REVIEW.value,
        QueueStatus.APPROVED.value,
        QueueStatus.SCHEDULED.value,
    }
    cleared = 0
    for item in repo.list_queue(limit=500):
        if item.get("status") not in live:
            continue
        created = (item.get("created_at") or "")[:10]
        scheduled = (item.get("scheduled_at") or "")[:10]
        if today in (created, scheduled):
            repo.transition(item["id"], QueueStatus.REJECTED)
            cleared += 1
    return cleared
