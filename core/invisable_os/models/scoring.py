"""Scoring & guardrail models.

The :class:`ScoreCard` encodes *exactly* what INVISABLE OS optimises for. The
weights are deliberately tilted so that trust and community value dominate reach —
this is the Prime Directive expressed numerically.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from invisable_os.models.content import ContentCandidate

# The dimensions the platform optimises FOR, with their relative weights.
# Trust and community value are weighted highest on purpose: reach must never be
# bought at their expense. These weights sum to 1.0.
SCORE_WEIGHTS: dict[str, float] = {
    "trust": 0.20,
    "community_value": 0.16,
    "authenticity": 0.14,
    "awareness": 0.12,
    "education": 0.12,
    "humour": 0.08,
    "consistency": 0.08,
    "long_term_brand": 0.10,
}


class ScoreCard(BaseModel):
    """A multi-criteria score for a candidate. Each field is 0.0 – 1.0."""

    trust: float = Field(default=0.0, ge=0.0, le=1.0)
    community_value: float = Field(default=0.0, ge=0.0, le=1.0)
    authenticity: float = Field(default=0.0, ge=0.0, le=1.0)
    awareness: float = Field(default=0.0, ge=0.0, le=1.0)
    education: float = Field(default=0.0, ge=0.0, le=1.0)
    humour: float = Field(default=0.0, ge=0.0, le=1.0)
    consistency: float = Field(default=0.0, ge=0.0, le=1.0)
    long_term_brand: float = Field(default=0.0, ge=0.0, le=1.0)

    rationale: str = Field(default="")

    def weighted_total(self) -> float:
        """Single composite score in 0.0 – 1.0, using :data:`SCORE_WEIGHTS`."""
        return round(
            sum(getattr(self, dim) * weight for dim, weight in SCORE_WEIGHTS.items()),
            4,
        )


class GuardrailVerdict(BaseModel):
    """The output of the hard-gate guardrail check.

    ``violations`` are hard failures (block publication). ``risk_flags`` are
    advisory — high-stakes content (medical/legal/benefits/sponsor/copyright) that
    a human must review before publishing, but which is not auto-blocked.
    ``swear_level`` records the strongest profanity detected (none/light/moderate/
    strong) so downstream policy can decide.
    """

    passed: bool
    violations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    swear_level: str = "none"

    @property
    def blocked(self) -> bool:
        return not self.passed

    @property
    def needs_human_review(self) -> bool:
        """Passed the hard gate but carries advisory risk flags."""
        return self.passed and bool(self.risk_flags)


class ScoredCandidate(BaseModel):
    """A candidate paired with its guardrail verdict and score."""

    candidate: ContentCandidate
    guardrail: GuardrailVerdict
    scorecard: ScoreCard
    improvement_passes: int = 0

    @property
    def total(self) -> float:
        """Composite score, forced to zero if a hard gate failed."""
        if self.guardrail.blocked:
            return 0.0
        return self.scorecard.weighted_total()
