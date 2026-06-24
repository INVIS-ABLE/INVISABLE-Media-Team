"""Sensible default posting schedule.

Three slots a day on weekdays at deliberately off-round, human-feeling times (a
pattern these schedulers use to avoid every account posting on the hour). Used by
``invisable seed-channels`` to get a brand posting consistently from day one.
"""

from __future__ import annotations

from invisable_os.models.scheduling import ScheduleSlot

# (hour, minute) — morning, lunch, evening. Off-the-hour on purpose.
DEFAULT_TIMES = ((8, 7), (12, 33), (17, 47))
WEEKDAYS = range(5)  # Monday–Friday


def default_week(channel_id: str) -> list[ScheduleSlot]:
    """A Mon–Fri × 3-slots-a-day schedule for a channel."""
    return [
        ScheduleSlot(channel_id=channel_id, weekday=day, hour=h, minute=m)
        for day in WEEKDAYS
        for (h, m) in DEFAULT_TIMES
    ]
