"""Scheduling service — fill the next open posting slot (the borrowed queue pattern).

``schedule_next`` takes an approved queue item and assigns it the earliest free slot
across the matching channel's weekly schedule, so the brand posts consistently
without anyone picking a time per post.
"""

from __future__ import annotations

from datetime import UTC, datetime

from invisable_os.engines import rank_posting_slots
from invisable_os.scheduling import calendar_by_day, next_open_slot
from invisable_os.store import Repository, get_repository

# Engagement metrics that signal genuine resonance — what "best time" optimises for.
_ENGAGEMENT_METRICS = {
    "saves", "shares", "story_submissions", "comments", "watch_time", "retention",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _channel_for_platform(repo: Repository, platform: str) -> dict | None:
    for ch in repo.list_channels():
        if ch["active"] and ch["platform"] == platform:
            return ch
    return None


def schedule_next(
    item_id: str,
    *,
    repository: Repository | None = None,
    after: datetime | None = None,
) -> dict:
    """Assign an item to the next open slot for its platform's channel."""
    repo = repository or get_repository()
    item = repo.get_queue_item(item_id)
    if item is None:
        return {"error": "not found", "id": item_id}

    channel = _channel_for_platform(repo, item.get("platform", ""))
    if channel is None:
        return {"error": "no active channel for platform", "platform": item.get("platform")}

    slots = repo.list_slots(channel["id"])
    if not slots:
        return {"error": "no posting slots configured for channel", "channel": channel["name"]}

    when = next_open_slot(
        slots,
        after=after or _now(),
        taken=repo.taken_slots(),
        tz=channel.get("timezone", "Europe/London"),
    )
    if when is None:
        return {"error": "no open slot within horizon"}

    updated = repo.assign_schedule(item_id, when)
    return {
        "id": item_id,
        "scheduled_at": updated["scheduled_at"],
        "channel": channel["name"],
        "status": updated["status"],
    }


def suggest_post_times(
    *,
    item_id: str | None = None,
    platform: str | None = None,
    theme: str | None = None,
    top: int = 3,
    repository: Repository | None = None,
) -> dict:
    """Suggest the best posting slots, learned from when published posts performed.

    Joins each performance signal to its post's actual ``published_at`` time, buckets
    engagement by weekday + hour (optionally narrowed to a platform/theme), and ranks
    the slots that beat the average. When ``item_id`` is given, the platform and theme
    are inferred from that queued post so the suggestion is tailored to it. Degrades to
    an empty suggestion list (never an error) when there isn't enough history yet.
    """
    repo = repository or get_repository()

    if item_id is not None:
        item = repo.get_queue_item(item_id)
        if item is None:
            return {"error": "not found", "id": item_id}
        candidate = item.get("candidate") or {}
        platform = platform or item.get("platform") or candidate.get("platform")
        if theme is None:
            themes = candidate.get("themes") or []
            theme = themes[0] if themes else None

    # When did each post actually go out? (published_at on the queue item.)
    published_at: dict[str, str] = {}
    for it in repo.list_queue(limit=1000):
        when = it.get("published_at")
        cid = it.get("candidate_id")
        if when and cid:
            published_at[cid] = when

    observations = []
    for s in repo.list_signals():
        if s["metric"] not in _ENGAGEMENT_METRICS:
            continue
        if platform and s.get("platform") and s["platform"] != platform:
            continue
        if theme and theme not in (s.get("themes") or []):
            continue
        when = published_at.get(s["candidate_id"])
        if not when:
            continue
        try:
            dt = datetime.fromisoformat(when)
        except ValueError:
            continue
        observations.append({"weekday": dt.weekday(), "hour": dt.hour, "value": s["value"]})

    return {
        "item_id": item_id,
        "platform": platform,
        "theme": theme,
        "observations": len(observations),
        "suggestions": rank_posting_slots(observations, top=top),
    }


def calendar(*, repository: Repository | None = None) -> dict:
    """Return scheduled items grouped by day, for a calendar view."""
    repo = repository or get_repository()
    from invisable_os.models.content import QueueStatus

    scheduled = repo.list_queue(QueueStatus.SCHEDULED.value, limit=500)
    return calendar_by_day(scheduled)
