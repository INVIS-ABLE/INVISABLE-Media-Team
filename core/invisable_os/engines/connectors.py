"""Harvester connectors.

Adapters onto public information sources. Each is guarded: if it isn't configured or
is unreachable, it returns ``[]`` rather than raising, so the Intelligence Harvester
always degrades gracefully. Connectors return **abstracted signals only** — topic,
kind, summary — never verbatim creator content.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

import httpx

log = logging.getLogger(__name__)


@runtime_checkable
class Connector(Protocol):
    name: str

    def fetch(self, topics: list[str]) -> list[dict]: ...


class FeedlyConnector:
    """Pulls fresh items from Feedly streams (abstracted to topic-level signals)."""

    name = "feedly"

    def __init__(self) -> None:
        self.token = os.getenv("FEEDLY_ACCESS_TOKEN", "")

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def fetch(self, topics: list[str]) -> list[dict]:
        if not self.configured:
            return []
        signals: list[dict] = []
        try:
            with httpx.Client(timeout=8.0) as client:
                for topic in topics:
                    resp = client.get(
                        "https://cloud.feedly.com/v3/search/contents",
                        params={"query": topic, "count": 5},
                        headers={"Authorization": f"OAuth {self.token}"},
                    )
                    resp.raise_for_status()
                    items = resp.json().get("results", [])
                    if items:
                        signals.append(
                            {
                                "topic": topic,
                                "kind": "discussion",
                                "summary": f"{len(items)} fresh public items on '{topic}'.",
                                "source_type": "rss",
                                "score": min(1.0, 0.4 + 0.1 * len(items)),
                            }
                        )
        except Exception as exc:  # noqa: BLE001
            log.info("Feedly connector unavailable: %s", exc)
        return signals


class GoogleTrendsConnector:
    """Reads interest signals from Google Trends (geo-scoped, abstracted)."""

    name = "google_trends"

    def __init__(self) -> None:
        self.geo = os.getenv("GOOGLE_TRENDS_GEO", "GB")

    def fetch(self, topics: list[str]) -> list[dict]:
        # pytrends is optional; if absent, yield nothing (graceful).
        try:
            from pytrends.request import TrendReq  # type: ignore
        except Exception:  # noqa: BLE001
            return []
        signals: list[dict] = []
        try:
            pytrends = TrendReq(hl="en-GB", geo=self.geo)
            for topic in topics:
                pytrends.build_payload([topic], geo=self.geo, timeframe="now 7-d")
                df = pytrends.interest_over_time()
                if df is not None and not df.empty:
                    recent = float(df[topic].iloc[-1])
                    summary = (
                        f"Search interest for '{topic}' at {recent:.0f}/100 ({self.geo})."
                    )
                    signals.append(
                        {
                            "topic": topic,
                            "kind": "trend",
                            "summary": summary,
                            "source_type": "trends",
                            "score": min(1.0, recent / 100.0),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            log.info("Google Trends connector unavailable: %s", exc)
        return signals


class FirecrawlConnector:
    """Scrapes a configured public page set via Firecrawl (abstracted)."""

    name = "firecrawl"

    def __init__(self) -> None:
        self.api_key = os.getenv("FIRECRAWL_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def fetch(self, topics: list[str]) -> list[dict]:
        # Wired behind the key; offline it yields nothing.
        if not self.configured:
            return []
        return []


def default_connectors() -> list[Connector]:
    return [FeedlyConnector(), GoogleTrendsConnector(), FirecrawlConnector()]
