"""Slot computation & calendar grouping.

``next_open_slot`` finds the earliest future posting time that matches one of a
channel's weekly slots and isn't already taken — the core "add to queue" mechanic.
Times are computed in the channel's timezone and returned as timezone-aware UTC.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from invisable_os.models.scheduling import ScheduleSlot


def next_open_slot(
    slots: list[ScheduleSlot],
    *,
    after: datetime,
    taken: set[datetime] | None = None,
    tz: str = "Europe/London",
    horizon_days: int = 21,
) -> datetime | None:
    """Earliest slot strictly after ``after`` that isn't in ``taken`` (UTC, aware).

    ``after`` and ``taken`` may be naive (assumed UTC) or aware. Returns ``None`` if
    no active slot falls within ``horizon_days``.
    """
    active = [s for s in slots if s.active]
    if not active:
        return None

    zone = ZoneInfo(tz)
    after_utc = _as_utc(after)
    taken_utc = {_as_utc(t) for t in (taken or set())}
    after_local = after_utc.astimezone(zone)

    for day_offset in range(horizon_days + 1):
        day = (after_local + timedelta(days=day_offset)).date()
        weekday = day.weekday()
        day_slots = sorted(
            (s for s in active if s.weekday == weekday), key=lambda s: (s.hour, s.minute)
        )
        for slot in day_slots:
            candidate_local = datetime(
                day.year, day.month, day.day, slot.hour, slot.minute, tzinfo=zone
            )
            candidate = candidate_local.astimezone(UTC)
            if candidate > after_utc and candidate not in taken_utc:
                return candidate
    return None


def calendar_by_day(items: list[dict], *, date_key: str = "scheduled_at") -> dict[str, list[dict]]:
    """Group scheduled queue items by ISO date for a calendar view."""
    out: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        value = item.get(date_key)
        if not value:
            continue
        out[value[:10]].append(item)
    return {day: out[day] for day in sorted(out)}


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
