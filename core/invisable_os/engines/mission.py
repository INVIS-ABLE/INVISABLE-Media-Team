"""Mission Advisor / Mission Alignment Engine.

The most valuable engine in the platform. The point of INVISABLE OS is not to
produce 20 posts a day — it is to produce 20 posts a day that *move INVISABLE
forward*. Every idea is checked against five mission impacts and scored, so the
agency behaves like a media organisation, not a content factory.

    awareness · community · fundraising · partner · long-term mission

Long-term mission impact is weighted highest: a quick spike that doesn't build the
movement is worth less than something that compounds.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from invisable_os.models.content import ContentCandidate

# Weights for the composite mission score (sum to 1.0). Long-term leads.
MISSION_WEIGHTS: dict[str, float] = {
    "awareness_impact": 0.22,
    "community_impact": 0.22,
    "long_term_mission_impact": 0.28,
    "fundraising_impact": 0.14,
    "partner_impact": 0.14,
}

# Heuristic markers per impact dimension (offline scoring; an LLM pass refines it).
_AWARENESS = (
    "invisible illness", "invisible illnesses", "chronic", "you can't see", "looks fine",
    "hidden", "unseen", "invisable", "raise awareness", "understand",
)
_COMMUNITY = (
    "you're not alone", "share your", "our community", "we", "support", "if this is you",
    "tell me", "you matter", "together",
)
_FUNDRAISING = (
    "donate", "fundraiser", "support the cause", "every pound", "help us", "gofundme",
    "justgiving", "charity",
)
_PARTNER = (
    "ct1", "gt insurance", "bald builders", "partner", "sponsor", "ambassador", "in partnership",
)
_LONG_TERM = (
    "mission", "movement", "why i started", "founder", "building", "long-term", "change",
    "no overclaiming", "honestly", "the reality",
)


class MissionScore(BaseModel):
    """Five mission impacts (0.0–1.0 each) plus a verdict."""

    awareness_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    community_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    fundraising_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    partner_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    long_term_mission_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    verdict: str = "hold"
    rationale: str = ""

    def total(self) -> float:
        return round(sum(getattr(self, d) * w for d, w in MISSION_WEIGHTS.items()), 4)


def _density(text: str, markers: tuple[str, ...], saturate: int = 2) -> float:
    lowered = text.lower()
    hits = sum(1 for m in markers if m in lowered)
    return min(hits / saturate, 1.0)


class MissionEngine:
    """Scores any idea or candidate against the INVISABLE® mission."""

    def advise(self, candidate: ContentCandidate) -> MissionScore:
        text = candidate.full_text
        awareness = _density(text, _AWARENESS)
        community = _density(text, _COMMUNITY)
        fundraising = _density(text, _FUNDRAISING)
        partner = _density(text, _PARTNER)
        long_term = _density(text, _LONG_TERM)
        if candidate.founder_centred:
            long_term = min(1.0, long_term + 0.3)

        score = MissionScore(
            awareness_impact=round(awareness, 3),
            community_impact=round(community, 3),
            fundraising_impact=round(fundraising, 3),
            partner_impact=round(partner, 3),
            long_term_mission_impact=round(long_term, 3),
        )
        total = score.total()
        # Verdict: advance (clearly moves the mission), hold (fine but unremarkable),
        # reject (does nothing for the mission — a content-factory post).
        if total >= 0.45:
            score.verdict = "advance"
        elif total >= 0.2:
            score.verdict = "hold"
        else:
            score.verdict = "reject"
        score.rationale = (
            f"mission={total} (awareness={score.awareness_impact}, "
            f"community={score.community_impact}, long_term={score.long_term_mission_impact}, "
            f"fundraising={score.fundraising_impact}, partner={score.partner_impact})"
        )
        return score
