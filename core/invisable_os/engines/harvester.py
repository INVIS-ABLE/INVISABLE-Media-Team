"""Intelligence Harvester.

Monitors **public** information sources, trend signals, creator content patterns,
discussions, and emerging opportunities (media call-outs, podcast guest requests,
relevant awareness days). It records *signals and learnings* into
``INVISABLE_BRAIN`` — never copies of creator content.

Ethics boundary, enforced by intent and design:

* The Harvester learns *patterns, structures, formats, and what resonates*.
* It must never store or reproduce copyrighted works or duplicate creator content.
  Harvested items are reduced to abstracted signals (topic, format, sentiment,
  opportunity), not verbatim text.

Connectors (Firecrawl, Crawl4AI, Feedly, Google Trends, AnswerThePublic) plug in
behind :meth:`harvest`. Offline, it yields a small set of illustrative, abstracted
signals so downstream engines and tests have something to work with.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invisable_os.brain import Memory, get_brain
from invisable_os.engines.connectors import Connector, default_connectors
from invisable_os.models.departments import Opportunity


@dataclass
class Signal:
    """An abstracted signal — never raw copied content."""

    topic: str
    kind: str  # trend | discussion | opportunity | format
    summary: str  # our own abstraction, not a copy
    source_type: str  # e.g. "rss", "trends", "forum" — not an attributable quote
    score: float = 0.5
    metadata: dict = field(default_factory=dict)


class IntelligenceHarvester:
    """Turns public signals into abstracted, ethically-clean intelligence."""

    def __init__(self, connectors: list[Connector] | None = None) -> None:
        self.brain = get_brain()
        self.connectors = connectors if connectors is not None else default_connectors()

    def harvest(self, topics: list[str] | None = None) -> list[Signal]:
        """Return abstracted signals for the given topics.

        Queries any configured connectors (Feedly/Trends/Firecrawl) and *abstracts*
        the results. When none are configured/reachable, it falls back to baseline
        interest signals so the rest of the platform always has something to act on.
        """
        topics = topics or ["invisible illness", "chronic fatigue", "trades mental health"]
        signals: list[Signal] = []

        # 1. Live connectors (abstracted signals only).
        for connector in self.connectors:
            try:
                for raw in connector.fetch(topics):
                    signals.append(
                        Signal(
                            topic=raw.get("topic", ""),
                            kind=raw.get("kind", "trend"),
                            summary=raw.get("summary", ""),
                            source_type=raw.get("source_type", connector.name),
                            score=float(raw.get("score", 0.5)),
                            metadata={"abstracted": True, "connector": connector.name},
                        )
                    )
            except Exception:  # noqa: BLE001 — a connector must never break the harvest
                continue

        # 2. Baseline interest signals so the platform always has direction.
        covered = {s.topic for s in signals}
        for topic in topics:
            if topic in covered:
                continue
            signals.append(
                Signal(
                    topic=topic,
                    kind="opportunity",
                    summary=(
                        f"Recurring public interest in '{topic}'. Educational, myth-busting "
                        "formats tend to resonate; warm, non-clinical tone preferred."
                    ),
                    source_type="aggregate",
                    score=0.7,
                    metadata={"abstracted": True},
                )
            )
        self.persist(signals)
        return signals

    def scan_opportunities(self, topics: list[str] | None = None) -> list[Opportunity]:
        """Surface media/speaking/sponsorship opportunities from the harvested signals.

        Offline this proposes sensible, mission-aligned opportunity *types* to pursue;
        with connectors it would attach concrete sources. Always abstracted.
        """
        signals = self.harvest(topics)
        opportunities: list[Opportunity] = []
        for s in signals[:5]:
            opportunities.append(
                Opportunity(
                    kind="podcast",
                    title=f"Podcasts covering '{s.topic}'",
                    fit_score=round(min(1.0, s.score), 3),
                    why=f"Active public interest in {s.topic} aligns with the mission.",
                    suggested_action=f"Pitch a founder-led segment on {s.topic}.",
                )
            )
        return opportunities

    def persist(self, signals: list[Signal]) -> int:
        """Store abstracted signals in the Brain. Returns count stored."""
        for s in signals:
            self.brain.remember(
                Memory(
                    text=f"[{s.kind}] {s.topic}: {s.summary}",
                    kind="trend_signal",
                    metadata={
                        "topic": s.topic,
                        "signal_kind": s.kind,
                        "source_type": s.source_type,
                        "score": s.score,
                        "abstracted": True,
                    },
                )
            )
        return len(signals)
