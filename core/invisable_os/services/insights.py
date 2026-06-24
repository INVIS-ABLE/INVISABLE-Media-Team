"""Insights service — surface theme performance alerts from recorded signals.

Reads the performance-signal history, compares each theme/metric's latest week to a
rolling baseline (:func:`detect_theme_alerts`), and returns ranked, plain-English
alerts for the dashboard's Insights view. Safe and empty until enough history exists.
"""

from __future__ import annotations

from datetime import UTC, datetime

from invisable_os.engines import detect_theme_alerts
from invisable_os.store import Repository, get_repository


def theme_alerts(
    *,
    baseline_weeks: int = 4,
    min_change: float = 0.20,
    now: datetime | None = None,
    repository: Repository | None = None,
) -> dict:
    """Detect theme/metric performance shifts vs the recent baseline."""
    repo = repository or get_repository()
    signals = repo.list_signals()
    alerts = detect_theme_alerts(
        signals,
        now=now or datetime.now(UTC),
        baseline_weeks=baseline_weeks,
        min_change=min_change,
    )
    momentum = sum(1 for a in alerts if a["direction"] == "up")
    return {
        "count": len(alerts),
        "momentum": momentum,
        "declining": len(alerts) - momentum,
        "alerts": alerts,
    }
