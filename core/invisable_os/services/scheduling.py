"""Scheduling service — fill the next open posting slot (the borrowed queue pattern).

``schedule_next`` takes an approved queue item and assigns it the earliest free slot
across the matching channel's weekly schedule, so the brand posts consistently
without anyone picking a time per post.
"""

from __future__ import annotations

from datetime import UTC, datetime

from invisable_os.scheduling import calendar_by_day, next_open_slot
from invisable_os.store import Repository, get_repository


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


def calendar(*, repository: Repository | None = None) -> dict:
    """Return scheduled items grouped by day, for a calendar view."""
    repo = repository or get_repository()
    from invisable_os.models.content import QueueStatus

    scheduled = repo.list_queue(QueueStatus.SCHEDULED.value, limit=500)
    return calendar_by_day(scheduled)
