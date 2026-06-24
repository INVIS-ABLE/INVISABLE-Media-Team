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

    def __init__(self) -> None:
        self.brain = get_brain()

    def harvest(self, topics: list[str] | None = None) -> list[Signal]:
        """Return abstracted signals for the given topics.

        With connectors configured this would query Feedly/Trends/Firecrawl and
        *abstract* the results. Offline it returns illustrative signals so the rest of
        the platform can operate end to end.
        """
        topics = topics or ["invisible illness", "chronic fatigue", "trades mental health"]
        signals: list[Signal] = []
        for topic in topics:
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
