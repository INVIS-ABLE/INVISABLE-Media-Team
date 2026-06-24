"""Metricool client — pull post performance and map it into Watchtower signals.

Closes the learning loop: real platform metrics → :class:`PerformanceSignal`s →
``AlgorithmWatchtower.ingest`` → learnings + the Founder Recognition Index.

Unconfigured/unreachable, ``fetch`` returns ``[]`` so the metrics sync is a safe
no-op offline. The client accepts an injectable ``httpx.Client`` for testing.
"""

from __future__ import annotations

import logging
import os

import httpx

from invisable_os.models.metrics import PerformanceSignal, SuccessMetric

log = logging.getLogger(__name__)

# Map Metricool metric keys → our SuccessMetric vocabulary. Unmapped keys are ignored.
METRIC_MAP: dict[str, SuccessMetric] = {
    "shares": SuccessMetric.SHARES,
    "saves": SuccessMetric.SAVES,
    "saved": SuccessMetric.SAVES,
    "comments": SuccessMetric.COMMENTS,
    "profileVisits": SuccessMetric.PROFILE_VISITS,
    "profile_visits": SuccessMetric.PROFILE_VISITS,
    "followersGained": SuccessMetric.FOLLOWER_GROWTH,
    "follower_growth": SuccessMetric.FOLLOWER_GROWTH,
    "watchTime": SuccessMetric.WATCH_TIME,
    "watch_time": SuccessMetric.WATCH_TIME,
    "retention": SuccessMetric.RETENTION,
    "websiteClicks": SuccessMetric.WEBSITE_VISITS,
    "website_visits": SuccessMetric.WEBSITE_VISITS,
}


class MetricoolClient:
    def __init__(
        self,
        api_token: str | None = None,
        blog_id: str | None = None,
        *,
        base_url: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_token = api_token or os.getenv("METRICOOL_API_TOKEN", "")
        self.blog_id = blog_id or os.getenv("METRICOOL_BLOG_ID", "")
        self.base_url = (base_url or os.getenv("METRICOOL_BASE_URL", "https://app.metricool.com")).rstrip("/")
        self._client = client or httpx.Client(timeout=20.0)

    @property
    def configured(self) -> bool:
        return bool(self.api_token and self.blog_id)

    def fetch(self, *, start: str, end: str) -> list[dict]:
        """Return raw post-metric records for the date range (``[]`` if unconfigured)."""
        if not self.configured:
            return []
        try:
            resp = self._client.get(
                f"{self.base_url}/api/v2/analytics/posts",
                params={"blogId": self.blog_id, "start": start, "end": end},
                headers={"X-Mc-Auth": self.api_token},
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:  # noqa: BLE001 — never break the metrics sync
            log.warning("Metricool fetch failed: %s", exc)
            return []


def metricool_to_signals(records: list[dict]) -> list[PerformanceSignal]:
    """Map raw Metricool records into PerformanceSignals (one per known metric)."""
    signals: list[PerformanceSignal] = []
    for rec in records:
        candidate_id = str(rec.get("candidateId") or rec.get("id") or "")
        platform = str(rec.get("provider") or rec.get("network") or "")
        metrics = rec.get("metrics", rec)
        for key, metric in METRIC_MAP.items():
            if key in metrics and metrics[key] is not None:
                try:
                    value = float(metrics[key])
                except (TypeError, ValueError):
                    continue
                signals.append(
                    PerformanceSignal(
                        candidate_id=candidate_id, platform=platform, metric=metric, value=value
                    )
                )
    return signals
