"""The Credible Source Rule — fact-led content must carry a credible source.

This is the fact-attribution equivalent of the brand guardrails: a deterministic,
dependency-free check that decides whether a piece of content is **fact-led** and,
if so, whether it has a credible source attached. A fact-led post with no source is
held for sourcing — *the platform must never present a social-media rumour as a fact*.

It also ranks sources by a credibility hierarchy (official UK gov → NHS/ONS/Parliament
→ broadcasters → trade bodies → charities → academic → trade media → social) and
formats clean attribution lines ("Source: ONS", "According to BBC News…").

Everything here is deterministic and offline-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# The preferred source hierarchy from the V3 spec, as credibility tiers (1 = best).
# Maps a source_type token → (tier, human label).
CREDIBILITY_HIERARCHY: dict[str, tuple[int, str]] = {
    "gov": (1, "Official UK government"),
    "parliament": (1, "UK Parliament"),
    "nhs": (2, "NHS / NICE"),
    "nice": (2, "NHS / NICE"),
    "ons": (2, "Office for National Statistics"),
    "broadcaster": (3, "Major UK broadcaster / news outlet"),
    "news": (3, "Major UK broadcaster / news outlet"),
    "trade_body": (4, "Recognised trade body"),
    "construction_press": (4, "Recognised construction publication"),
    "charity": (5, "Established charity"),
    "academic": (6, "Academic / research"),
    "research": (6, "Academic / research"),
    "trade_media": (7, "Reputable trade media"),
    "social": (8, "Social / community (lived experience only — not hard facts)"),
}

# The lowest credibility tier that may still back a *hard fact*. Social/community
# sources (tier 8) are for lived experience only, never for hard facts.
MAX_TIER_FOR_FACTS = 7

# Markers that make a piece of content "fact-led" (and therefore source-requiring).
_STAT_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|per ?cent|percent|million|billion|k\b)", re.I)
_PERCENT_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s?%")
_YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
_FACT_PHRASES = (
    "according to", "research shows", "studies show", "study found", "a study",
    "figures show", "government figures", "official figures", "data shows",
    "statistics show", "reported that", "reports that", "survey found",
    "nhs says", "ons", "office for national statistics", "department for",
    "new law", "legislation", "regulation requires", "benefits", "universal credit",
    "scientists", "researchers", "clinical", "diagnosed with",
)
# Topic markers that strongly imply a hard claim was made.
_CLAIM_TOPICS = (
    "tool theft", "van theft", "construction output", "apprenticeship",
    "waiting list", "waiting times", "employment rate", "unemployment",
    "sick pay", "pip", "disability benefit",
)


@dataclass
class FactCheckVerdict:
    """The outcome of a credible-source check on a piece of content."""

    fact_led: bool
    has_source: bool
    ok: bool  # True unless it's fact-led with no (sufficiently credible) source
    reasons: list[str] = field(default_factory=list)  # why it was flagged fact-led
    attributions: list[str] = field(default_factory=list)  # clean "Source: …" lines
    weak_sources: list[str] = field(default_factory=list)  # sources too weak for facts
    advisory: str = ""

    def as_dict(self) -> dict:
        return {
            "fact_led": self.fact_led,
            "has_source": self.has_source,
            "ok": self.ok,
            "reasons": self.reasons,
            "attributions": self.attributions,
            "weak_sources": self.weak_sources,
            "advisory": self.advisory,
        }


def credibility(source_type: str) -> tuple[int, str]:
    """Return the (tier, label) for a source type; unknown types are mid-low (tier 7)."""
    key = (source_type or "").strip().lower()
    return CREDIBILITY_HIERARCHY.get(key, (7, "Unclassified source"))


def is_fact_led(text: str) -> tuple[bool, list[str]]:
    """Decide whether ``text`` makes a fact-led claim, with the reasons it tripped."""
    lowered = (text or "").lower()
    reasons: list[str] = []
    if _PERCENT_PATTERN.search(text or ""):
        reasons.append("contains a percentage")
    elif _STAT_PATTERN.search(text or ""):
        reasons.append("contains a statistic / large number")
    for phrase in _FACT_PHRASES:
        if phrase in lowered:
            reasons.append(f"uses a fact-claim phrase: '{phrase}'")
            break
    for topic in _CLAIM_TOPICS:
        if topic in lowered:
            reasons.append(f"makes a claim about '{topic}'")
            break
    # A bare year on its own is weak; only count it alongside another signal.
    if _YEAR_PATTERN.search(text or "") and reasons:
        reasons.append("cites a specific year")
    return (len(reasons) > 0, reasons)


def attribution_line(source: dict, *, style: str = "label") -> str:
    """A clean, non-cluttered attribution line for a source.

    ``style="label"`` → "Source: ONS"; ``style="prose"`` → "According to ONS…".
    """
    name = source.get("name", "source")
    if style == "prose":
        return f"According to {name}…"
    return f"Source: {name}"


def check_post(text: str, sources: list[dict] | None = None) -> FactCheckVerdict:
    """Run the Credible Source Rule over a post and its attached sources.

    A fact-led post is ``ok`` only if at least one attached source is credible enough
    (tier ≤ 7) to back a hard fact. Sources too weak for facts are surfaced separately
    so the operator can attach a stronger one rather than silently shipping a rumour.
    """
    sources = sources or []
    fact_led, reasons = is_fact_led(text)

    attributions: list[str] = []
    weak: list[str] = []
    has_credible = False
    for src in sources:
        tier, _label = credibility(src.get("source_type", ""))
        if tier <= MAX_TIER_FOR_FACTS:
            has_credible = True
            attributions.append(attribution_line(src))
        else:
            weak.append(src.get("name", "unnamed source"))

    has_source = bool(sources)
    if not fact_led:
        return FactCheckVerdict(
            fact_led=False, has_source=has_source, ok=True,
            reasons=[], attributions=attributions, weak_sources=weak,
            advisory="Not fact-led — no source required, but attribution is welcome.",
        )

    ok = has_credible
    if ok:
        advisory = "Fact-led and sourced. Show a short attribution (e.g. 'Source: ONS')."
    elif weak:
        advisory = (
            "Fact-led but only weak sources attached — social/community sources are "
            "for lived experience, not hard facts. Attach an official/credible source."
        )
    else:
        advisory = (
            "Fact-led with NO source. Attach a credible source before approval — never "
            "present an unsourced claim as fact."
        )
    return FactCheckVerdict(
        fact_led=True, has_source=has_source, ok=ok,
        reasons=reasons, attributions=attributions, weak_sources=weak, advisory=advisory,
    )
