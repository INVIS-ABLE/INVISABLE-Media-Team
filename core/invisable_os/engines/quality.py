"""Quality Control Engine.

Scores every post across eleven dimensions out of 10. Anything below the threshold
on any dimension must be improved before it can enter the approval queue. This is
the bar that turns "a lot of content" into "content worth publishing".

The dimensions are sourced from the build directive:

    Hook · Relatability · Emotional strength · Humour · Platform fit · Brand fit ·
    Originality · Risk/sensitivity · Shareability · Mission alignment · Human authenticity
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.personality import personality_score
from invisable_os.engines.scoring import Scorer
from invisable_os.guardrails import check
from invisable_os.models.content import ContentCandidate

QUALITY_THRESHOLD = 8.0  # out of 10; anything below on any dimension → improve


class QualityScore(BaseModel):
    """Eleven dimensions, each 0–10. ``risk_sensitivity`` is inverted: 10 = safest."""

    hook: float = Field(default=0.0, ge=0.0, le=10.0)
    relatability: float = Field(default=0.0, ge=0.0, le=10.0)
    emotional_strength: float = Field(default=0.0, ge=0.0, le=10.0)
    humour: float = Field(default=0.0, ge=0.0, le=10.0)
    platform_fit: float = Field(default=0.0, ge=0.0, le=10.0)
    brand_fit: float = Field(default=0.0, ge=0.0, le=10.0)
    originality: float = Field(default=0.0, ge=0.0, le=10.0)
    risk_sensitivity: float = Field(default=0.0, ge=0.0, le=10.0)
    shareability: float = Field(default=0.0, ge=0.0, le=10.0)
    mission_alignment: float = Field(default=0.0, ge=0.0, le=10.0)
    human_authenticity: float = Field(default=0.0, ge=0.0, le=10.0)

    def dimensions(self) -> dict[str, float]:
        return self.model_dump()

    def average(self) -> float:
        vals = self.dimensions().values()
        return round(sum(vals) / len(vals), 2)

    def weakest(self) -> tuple[str, float]:
        return min(self.dimensions().items(), key=lambda kv: kv[1])

    def passes(self, threshold: float = QUALITY_THRESHOLD) -> bool:
        """Every dimension must meet the threshold to enter the approval queue."""
        return all(v >= threshold for v in self.dimensions().values())


class QualityEngine:
    """Computes the 11-dimension quality scorecard for a candidate."""

    def __init__(self, scorer: Scorer | None = None, mission: MissionEngine | None = None) -> None:
        self.scorer = scorer or Scorer()
        self.mission = mission or MissionEngine()

    def score(self, candidate: ContentCandidate) -> QualityScore:
        card = self.scorer.score(candidate)  # 0–1 value dimensions
        verdict = check(candidate)
        mission = self.mission.advise(candidate)
        text = candidate.full_text

        hook = 10.0 if candidate.hook.strip() else 3.0
        if candidate.hook.strip():
            # Stronger hook if it's punchy (short, ends with intrigue/question).
            hook = 7.0 + min(3.0, 3.0 * (len(candidate.hook) < 80))

        return QualityScore(
            hook=round(hook, 2),
            relatability=round(10 * max(card.community_value, personality_score(text)), 2),
            emotional_strength=round(10 * max(card.trust, card.community_value), 2),
            humour=round(10 * card.humour, 2),
            platform_fit=round(10 * card.consistency, 2),
            brand_fit=round(10.0 if verdict.passed else 0.0, 2),
            originality=round(10.0 if candidate.original else 0.0, 2),
            # Inverted risk: safest (10) when no advisory flags, drop per flag.
            risk_sensitivity=round(max(0.0, 10.0 - 3.0 * len(verdict.risk_flags)), 2),
            shareability=round(10 * max(card.community_value, card.awareness), 2),
            mission_alignment=round(10 * mission.total(), 2),
            human_authenticity=round(10 * card.authenticity, 2),
        )
