"""Source-led scanning — feed the swarm real topics from configured sources.

The Agent Swarm's scan stage can run on a fixed seed pool (offline) or, when credible
sources are configured, on **live headlines** pulled from their RSS feeds. This module
is that bridge: it reads the enabled ``source`` / ``scanner_source`` rows, fetches
recent items via a dependency-light RSS connector, routes each headline to the right
scanner bot by topic area, and — crucially — falls back to the seed pool for any bot
with nothing fresh, so the swarm always has something to work on.

Two boundaries are respected:

* **Graceful degradation** — no network / no feeds / a parse error yields the seed
  pool, never an exception. The full pipeline stays testable offline.
* **Abstraction, not reposting** — a fetched *headline* is used only as a *topic to
  brief original content*. We never store or reproduce article bodies; this mirrors
  the Intelligence Harvester's ethics boundary.
"""

from __future__ import annotations

import logging
from xml.etree import ElementTree as ET

import httpx

from invisable_os.store import Repository, get_repository

log = logging.getLogger(__name__)

# Route a source to a scanner bot by matching keywords against its topic_area /
# source_type. Order matters: the first bot whose keywords match wins.
_BOT_TOPIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Autoimmune & Invisible Illness Bot",
        ("autoimmune", "chronic", "fatigue", "invisible", "illness", "pain", "spoonie"),
    ),
    (
        "Construction Scanner Bot",
        ("construction", "tool", "van", "site", "apprentice", "build", "trade"),
    ),
    (
        "Trades Relatability Bot",
        ("self-employed", "self employed", "subbie", "sole trader", "plumber", "sparky"),
    ),
    (
        "Pop Culture Index Bot",
        ("pop", "culture", "film", "tv", "meme", "celebrity", "viral"),
    ),
    (
        "UK Source Scanner Bot",
        ("nhs", "gov", "ons", "parliament", "disability", "employment", "benefit", "charity"),
    ),
)

_MAX_ITEMS_PER_SOURCE = 5


def _route_bot(topic_area: str, source_type: str) -> str:
    """Pick the scanner bot a source belongs to (defaults to the UK source bot)."""
    haystack = f"{topic_area} {source_type}".lower()
    for bot, keywords in _BOT_TOPIC_KEYWORDS:
        if any(k in haystack for k in keywords):
            return bot
    return "UK Source Scanner Bot"


def fetch_rss_titles(url: str, *, limit: int = _MAX_ITEMS_PER_SOURCE) -> list[str]:
    """Best-effort RSS/Atom title fetch. Returns ``[]`` on any failure (offline-safe)."""
    if not url:
        return []
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "INVISABLE-OS/scanner"})
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
    except Exception as exc:  # noqa: BLE001 — a feed must never break a scan
        log.info("RSS fetch skipped for %s: %s", url, exc)
        return []
    titles: list[str] = []
    # RSS: channel/item/title · Atom: entry/title (namespaced).
    for tag in (".//item/title", ".//{http://www.w3.org/2005/Atom}entry/"
                "{http://www.w3.org/2005/Atom}title"):
        for el in root.findall(tag):
            text = (el.text or "").strip()
            if text:
                titles.append(text[:160])
            if len(titles) >= limit:
                return titles
    return titles


def gather_topics(
    fallback: dict[str, tuple[str, ...]],
    *,
    repository: Repository | None = None,
    live: bool = True,
) -> dict[str, list[str]]:
    """Topics per scanner bot, from live sources where available else the seed pool.

    ``fallback`` is the swarm's deterministic seed pool. Every scanner bot in it is
    always represented in the result, so the swarm never starves. ``live=False``
    skips all network and returns the seed pool verbatim (used by tests/offline).
    """
    repo = repository or get_repository()
    topics: dict[str, list[str]] = {bot: [] for bot in fallback}

    if live:
        for source in _enabled_feed_sources(repo):
            bot = _route_bot(source.get("topic_area", ""), source.get("source_type", ""))
            if bot not in topics:
                continue
            for title in fetch_rss_titles(source.get("rss_url") or source.get("url", "")):
                topics[bot].append(title)

    # Any bot with no live topics falls back to its seed pool.
    for bot, seeds in fallback.items():
        if not topics.get(bot):
            topics[bot] = list(seeds)
    return topics


def _enabled_feed_sources(repo: Repository) -> list[dict]:
    """Enabled sources that expose a feed URL — credible sources + scanner sources."""
    out: list[dict] = []
    for s in repo.list_sources(enabled=True):
        if s.get("rss_url") or s.get("url"):
            out.append(s)
    for s in repo.list_scanner_sources():
        if s.get("enabled", True) and (s.get("rss_url") or s.get("url")):
            out.append(
                {
                    "topic_area": s.get("topic_area", ""),
                    "source_type": s.get("type", ""),
                    "rss_url": s.get("rss_url", ""),
                    "url": s.get("url", ""),
                }
            )
    return out


# A small starter set of credible UK-first feeds, seeded on demand so the swarm has
# real sources to scan out of the box. RSS endpoints are public and stable.
DEFAULT_UK_SOURCES: tuple[dict, ...] = (
    {
        "name": "GOV.UK announcements",
        "source_type": "gov",
        "credibility_level": 1,
        "topic_area": "uk government disability employment benefits",
        "rss_url": "https://www.gov.uk/search/news-and-communications.atom",
    },
    {
        "name": "NHS News",
        "source_type": "nhs",
        "credibility_level": 2,
        "topic_area": "nhs health invisible illness chronic",
        "rss_url": "https://www.nhs.uk/news/feed/",
    },
    {
        "name": "Construction news (trade)",
        "source_type": "construction_press",
        "credibility_level": 4,
        "topic_area": "construction trades tool theft site apprentice",
        "rss_url": "",
    },
)


def seed_default_sources(*, repository: Repository | None = None) -> int:
    """Seed the starter UK feed set (idempotent by source name). Returns count added."""
    repo = repository or get_repository()
    existing = {s["name"] for s in repo.list_sources()}
    added = 0
    for src in DEFAULT_UK_SOURCES:
        if src["name"] in existing:
            continue
        repo.add_source(dict(src))
        added += 1
    return added
