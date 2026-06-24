"""Posting-time intelligence — learn when content actually performs, and suggest slots.

Fixed weekly slots post consistently but blindly. This engine learns from real
performance: given observations of *when a post went out* (weekday + hour) and *how
it did* (an engagement value), it ranks the time slots that beat the average and
predicts a lift. Pure and deterministic — the service joins published-at times to
performance signals and hands the observations here.
"""

from __future__ import annotations

from collections import defaultdict

WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _label(weekday: int, hour: int) -> str:
    name = WEEKDAY_NAMES[weekday] if 0 <= weekday < 7 else "?"
    return f"{name} {hour:02d}:00"


def rank_posting_slots(
    observations: list[dict],
    *,
    top: int = 3,
    min_samples: int = 2,
) -> list[dict]:
    """Rank (weekday, hour) slots by mean engagement, with a lift vs the overall average.

    ``observations`` are dicts with ``weekday`` (0=Mon … 6=Sun), ``hour`` (0–23), and
    ``value`` (an engagement number). A slot is only suggested once it has at least
    ``min_samples`` observations, so a single lucky post can't crown a time. Returns
    the ``top`` slots, best mean first.
    """
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for o in observations:
        try:
            weekday = int(o["weekday"])
            hour = int(o["hour"])
        except (KeyError, TypeError, ValueError):
            continue
        buckets[(weekday, hour)].append(float(o.get("value", 0.0)))

    all_values = [v for vs in buckets.values() for v in vs]
    if not all_values:
        return []
    overall = sum(all_values) / len(all_values)

    slots = []
    for (weekday, hour), values in buckets.items():
        if len(values) < min_samples:
            continue
        mean = sum(values) / len(values)
        lift = (mean - overall) / overall if overall > 0 else 0.0
        slots.append({
            "weekday": weekday,
            "hour": hour,
            "label": _label(weekday, hour),
            "mean": round(mean, 2),
            "samples": len(values),
            "lift_pct": round(lift * 100, 1),
        })

    slots.sort(key=lambda s: s["mean"], reverse=True)
    return slots[:top]
