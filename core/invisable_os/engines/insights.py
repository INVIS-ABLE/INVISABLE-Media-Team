"""Theme performance alerts — turn the Watchtower's quiet history into proactive nudges.

The Watchtower learns theme→metric correlations and charts the Founder Recognition
Index, but it never *tells* anyone when a theme's performance shifts. This module
compares each theme/metric's most recent week against a rolling baseline of the prior
weeks and emits plain-English alerts ("Humour is down 32% on saves vs the last 4
weeks") with a recommendation, so the dashboard can surface what to do next.

Pure and deterministic: :func:`detect_theme_alerts` takes signals (with ISO
``observed_at``) plus a ``now`` reference and returns ranked alerts. No wall-clock,
no I/O — the service layer supplies the data and the timestamp.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

WEEK = timedelta(days=7)

# Metrics worth alerting on — the ones that express genuine resonance or recognition.
# (Raw follower counts / impressions are noisier and less actionable, so we skip them.)
ALERT_METRICS = {
    "saves", "shares", "story_submissions", "comments", "watch_time", "retention",
    "media_mentions", "podcast_invitations", "speaking_opportunities",
    "partner_enquiries", "sponsor_enquiries", "profile_visits",
}


@dataclass
class ThemeAlert:
    theme: str
    metric: str
    direction: str          # "up" | "down"
    category: str           # "momentum" | "decline"
    change_pct: float       # signed, e.g. -32.0
    current_avg: float
    baseline_avg: float
    samples: int            # data points in the current window
    recommendation: str


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def detect_theme_alerts(
    signals: list[dict],
    *,
    now: datetime,
    baseline_weeks: int = 4,
    min_change: float = 0.20,
    min_samples: int = 2,
) -> list[dict]:
    """Flag themes whose latest-week performance diverges from their recent baseline.

    A theme/metric is alerted when the current 7-day window and the prior
    ``baseline_weeks`` both have at least ``min_samples`` readings and the relative
    change is at least ``min_change`` (e.g. 0.20 = 20%). Returns dicts sorted by the
    magnitude of the change, biggest mover first.
    """
    current_start = now - WEEK
    baseline_start = now - WEEK * (baseline_weeks + 1)

    current: dict[tuple[str, str], list[float]] = defaultdict(list)
    baseline: dict[tuple[str, str], list[float]] = defaultdict(list)

    for s in signals:
        metric = s.get("metric")
        if metric not in ALERT_METRICS:
            continue
        when = _parse(s.get("observed_at"))
        if when is None:
            continue
        value = float(s.get("value", 0.0))
        for theme in s.get("themes") or ["uncategorised"]:
            key = (theme, metric)
            if when >= current_start:
                current[key].append(value)
            elif baseline_start <= when < current_start:
                baseline[key].append(value)

    alerts: list[ThemeAlert] = []
    for key, cur_values in current.items():
        base_values = baseline.get(key, [])
        if len(cur_values) < min_samples or len(base_values) < min_samples:
            continue
        cur_avg = sum(cur_values) / len(cur_values)
        base_avg = sum(base_values) / len(base_values)
        if base_avg <= 0:
            continue
        change = (cur_avg - base_avg) / base_avg
        if abs(change) < min_change:
            continue
        theme, metric = key
        up = change > 0
        pretty = metric.replace("_", " ")
        if up:
            recommendation = (
                f"'{theme}' is resonating on {pretty} — keep this rhythm and lean in."
            )
        else:
            recommendation = (
                f"'{theme}' is fading on {pretty} — refresh the angle or rebalance "
                f"toward themes with momentum."
            )
        alerts.append(ThemeAlert(
            theme=theme,
            metric=metric,
            direction="up" if up else "down",
            category="momentum" if up else "decline",
            change_pct=round(change * 100, 1),
            current_avg=round(cur_avg, 2),
            baseline_avg=round(base_avg, 2),
            samples=len(cur_values),
            recommendation=recommendation,
        ))

    alerts.sort(key=lambda a: abs(a.change_pct), reverse=True)
    return [asdict(a) for a in alerts]
