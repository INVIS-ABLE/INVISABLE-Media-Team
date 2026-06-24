"""Founder Engine.

Two jobs:

1. Keep founder presence at roughly **80%** of published content (configurable via
   ``INVISABLE_FOUNDER_PRESENCE_TARGET``). Founder presence is what builds Stephen
   Garnham's recognition, credibility, reach and influence — *as a consequence of
   genuine impact*, never by fabrication.
2. Score how genuinely founder-centred a candidate is, and decide — given the
   current published mix — whether the next slot should be a founder piece.

The engine never invents founder experiences. It centres the founder's real voice,
perspective and advocacy; the guardrails block anything fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass

from invisable_os.config import get_settings
from invisable_os.models.content import ContentCandidate

# Signals that a piece authentically centres the founder.
FOUNDER_SIGNALS = (
    "stephen",
    "garnham",
    "founder",
    "i started",
    "i built",
    "my journey",
    "i live with",
    "i set up invisable",
    "as someone who",
    "i want you to know",
)


@dataclass
class FounderBalance:
    """A snapshot of founder presence in the published mix."""

    target: float
    current: float
    needs_founder_next: bool

    @property
    def gap(self) -> float:
        return round(self.target - self.current, 4)


class FounderEngine:
    """Maintains ~80% founder presence and scores founder-centredness."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def target(self) -> float:
        return self.settings.founder_presence_target

    def founder_strength(self, candidate: ContentCandidate) -> float:
        """0.0–1.0 measure of how genuinely founder-centred a candidate is."""
        if candidate.founder_centred:
            base = 0.6
        else:
            base = 0.0
        lowered = candidate.full_text.lower()
        hits = sum(1 for s in FOUNDER_SIGNALS if s in lowered)
        return round(min(1.0, base + 0.15 * hits), 3)

    def balance(self, published: list[ContentCandidate]) -> FounderBalance:
        """Given what's already published, report founder presence and what's needed."""
        if not published:
            return FounderBalance(target=self.target, current=0.0, needs_founder_next=True)
        founder_count = sum(1 for c in published if c.founder_centred)
        current = founder_count / len(published)
        return FounderBalance(
            target=self.target,
            current=round(current, 4),
            needs_founder_next=current < self.target,
        )

    def rebalance(
        self, selected: list[ContentCandidate], published: list[ContentCandidate] | None = None
    ) -> list[ContentCandidate]:
        """Reorder a selected set so the *running* published mix trends toward target.

        This is proportional, not greedy-to-the-max: it interleaves founder and
        non-founder pieces so the running founder share tracks ~80% rather than
        slamming to 100%. It never fabricates founder content — it only orders the
        candidates that already exist.
        """
        published = published or []
        founder = [c for c in selected if c.founder_centred]
        rest = [c for c in selected if not c.founder_centred]

        running_founder = sum(1 for c in published if c.founder_centred)
        running_total = len(published)

        result: list[ContentCandidate] = []
        fi = ri = 0
        while fi < len(founder) or ri < len(rest):
            ratio = running_founder / running_total if running_total else 0.0
            want_founder = ratio < self.target
            if want_founder and fi < len(founder):
                result.append(founder[fi])
                fi += 1
                running_founder += 1
            elif ri < len(rest):
                result.append(rest[ri])
                ri += 1
            elif fi < len(founder):  # only founder pieces remain
                result.append(founder[fi])
                fi += 1
                running_founder += 1
            running_total += 1
        return result
