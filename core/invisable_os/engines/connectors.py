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
    """Searches public web content via Firecrawl, abstracted to topic-level signals.

    Uses Firecrawl's ``/v1/search`` endpoint. Only the *count and topic* are kept —
    never verbatim page content — to honour the Harvester's ethics boundary. The
    HTTP transport is injectable so the abstraction is tested without a live API.
    """

    name = "firecrawl"

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.api_key = os.getenv("FIRECRAWL_API_KEY", "")
        self.base_url = os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev").rstrip("/")
        self.limit = int(os.getenv("FIRECRAWL_SEARCH_LIMIT", "5"))
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def fetch(self, topics: list[str]) -> list[dict]:
        if not self.configured:
            return []
        signals: list[dict] = []
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=12.0, transport=self._transport,
                headers={"Authorization": f"Bearer {self.api_key}"},
            ) as client:
                for topic in topics:
                    resp = client.post(
                        "/v1/search", json={"query": topic, "limit": self.limit}
                    )
                    resp.raise_for_status()
                    results = resp.json().get("data", []) if resp.content else []
                    signal = abstract_web_results(topic, results, source_type="web")
                    if signal:
                        signals.append(signal)
        except Exception as exc:  # noqa: BLE001 — degrade, never raise
            log.info("Firecrawl connector unavailable: %s", exc)
        return signals


class Crawl4AIConnector:
    """Crawls a configured set of public sources via a self-hosted Crawl4AI.

    Points at ``CRAWL4AI_BASE_URL`` and crawls the URLs in ``CRAWL4AI_SOURCES``
    (comma-separated), abstracting each reachable source into a topic-level signal —
    never verbatim content. Graceful: yields nothing when unconfigured/unreachable.
    """

    name = "crawl4ai"

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.base_url = os.getenv("CRAWL4AI_BASE_URL", "").rstrip("/")
        raw_sources = os.getenv("CRAWL4AI_SOURCES", "").split(",")
        self.sources = [s.strip() for s in raw_sources if s.strip()]
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.sources)

    def fetch(self, topics: list[str]) -> list[dict]:
        if not self.configured:
            return []
        signals: list[dict] = []
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=20.0, transport=self._transport
            ) as client:
                for url in self.sources:
                    resp = client.post("/crawl", json={"urls": [url]})
                    resp.raise_for_status()
                    payload = resp.json() if resp.content else {}
                    signal = abstract_crawl_result(url, payload, topics)
                    if signal:
                        signals.append(signal)
        except Exception as exc:  # noqa: BLE001
            log.info("Crawl4AI connector unavailable: %s", exc)
        return signals


# --- Pure abstraction helpers (ethics boundary: counts/topics, never verbatim) ---


def abstract_web_results(topic: str, results: list, *, source_type: str) -> dict | None:
    """Reduce a list of web search results to a single abstracted signal."""
    count = len(results or [])
    if not count:
        return None
    return {
        "topic": topic,
        "kind": "discussion",
        "summary": f"{count} fresh public results on '{topic}'.",
        "source_type": source_type,
        "score": min(1.0, 0.4 + 0.1 * count),
    }


def abstract_crawl_result(url: str, payload: dict, topics: list[str]) -> dict | None:
    """Reduce a Crawl4AI crawl response for one source to an abstracted signal."""
    results = payload.get("results") or payload.get("data") or []
    if not (payload.get("success", True) and results):
        return None
    topic = topics[0] if topics else url
    return {
        "topic": topic,
        "kind": "format",
        "summary": f"Scanned {url}: {len(results)} relevant item(s) for '{topic}'.",
        "source_type": "crawl",
        "score": min(1.0, 0.4 + 0.1 * len(results)),
    }


def default_connectors() -> list[Connector]:
    return [
        FeedlyConnector(),
        GoogleTrendsConnector(),
        FirecrawlConnector(),
        Crawl4AIConnector(),
    ]
