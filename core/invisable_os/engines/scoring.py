"""The Scorer — turns the platform's values into a number.

It produces a :class:`ScoreCard` for a candidate across the eight dimensions the
platform optimises for. The score is deterministic by default (fully testable and
fast at the volume of "hundreds of candidates daily"); an optional LLM pass can
refine the rationale and nuance where a key is configured.

Design principle: the scorer rewards substance (education, specificity, warmth,
community usefulness) and is structurally incapable of rewarding the things the
platform must never optimise for — those are handled upstream by the guardrails,
which zero out a blocked candidate's total.
"""

from __future__ import annotations

from invisable_os.brain import get_brain
from invisable_os.engines.cultural import CulturalIntelligenceEngine
from invisable_os.engines.founder import FounderEngine
from invisable_os.models.content import ContentCandidate
from invisable_os.models.scoring import ScoreCard

# Words that signal genuine educational / explanatory substance.
EDUCATION_MARKERS = (
    "because",
    "means",
    "for example",
    "the reason",
    "here's why",
    "how to",
    "what happens",
    "studies",
    "evidence",
    "let me explain",
    "the truth is",
)

# Words that signal community value — invitation, support, belonging.
COMMUNITY_MARKERS = (
    "you're not alone",
    "share your",
    "tell me",
    "we",
    "our community",
    "support",
    "comment if",
    "if this is you",
    "drop a",
    "let us know",
    "you matter",
)

# Words that signal trust — honesty, humility, non-overclaiming.
TRUST_MARKERS = (
    "honestly",
    "i won't pretend",
    "no quick fix",
    "it's hard",
    "the reality",
    "i don't have all the answers",
    "what helped me",
    "this isn't medical advice",
)

# Awareness markers — naming the invisible-illness mission clearly.
AWARENESS_MARKERS = (
    "invisible illness",
    "invisible illnesses",
    "chronic",
    "you can't see",
    "looks fine",
    "but i'm not",
    "hidden",
    "invisable",
)

# Light humour markers (used gently — humour is one of eight, never dominant).
HUMOUR_MARKERS = (
    "haha",
    "let's be honest",
    "plot twist",
    "nobody warned me",
    "the audacity",
    "iconic",
    "not me",
)


def _density(text: str, markers: tuple[str, ...], saturate: int = 2) -> float:
    lowered = text.lower()
    hits = sum(1 for m in markers if m in lowered)
    return min(hits / saturate, 1.0)


class Scorer:
    """Produces a ScoreCard for a candidate."""

    def __init__(
        self,
        cultural: CulturalIntelligenceEngine | None = None,
        founder: FounderEngine | None = None,
    ) -> None:
        self.cultural = cultural or CulturalIntelligenceEngine()
        self.founder = founder or FounderEngine()
        self.brain = get_brain()

    def score(self, candidate: ContentCandidate) -> ScoreCard:
        text = candidate.full_text
        notes: list[str] = []

        # --- the eight dimensions ------------------------------------------
        education = _density(text, EDUCATION_MARKERS, saturate=2)
        community_value = _density(text, COMMUNITY_MARKERS, saturate=2)
        trust = 0.4 + 0.6 * _density(text, TRUST_MARKERS, saturate=2)
        awareness = _density(text, AWARENESS_MARKERS, saturate=2)
        humour = _density(text, HUMOUR_MARKERS, saturate=2)

        cultural_score, cnotes = self.cultural.resonance(text)
        notes.extend(cnotes)

        # Authenticity blends honesty/trust markers, originality, and founder voice.
        founder_strength = self.founder.founder_strength(candidate)
        authenticity = round(
            0.5 * trust + 0.25 * (1.0 if candidate.original else 0.0) + 0.25 * founder_strength,
            3,
        )

        # Consistency rewards a clear hook + body + CTA structure and a sensible length.
        consistency = self._structure_score(candidate)

        # Long-term brand = mission alignment (awareness) + trust + cultural fit,
        # the things that compound rather than spike.
        long_term_brand = round(0.4 * awareness + 0.35 * trust + 0.25 * cultural_score, 3)

        card = ScoreCard(
            trust=round(trust, 3),
            community_value=round(community_value, 3),
            authenticity=authenticity,
            awareness=round(awareness, 3),
            education=round(education, 3),
            humour=round(humour, 3),
            consistency=consistency,
            long_term_brand=long_term_brand,
        )

        # --- learn from the past: nudge using Watchtower memory ------------
        card = self._apply_learnings(candidate, card)

        card.rationale = self._rationale(card, notes)
        return card

    def _structure_score(self, candidate: ContentCandidate) -> float:
        score = 0.0
        if candidate.hook.strip():
            score += 0.4
        if candidate.body.strip():
            score += 0.4
        if candidate.call_to_action.strip():
            score += 0.2
        length = len(candidate.full_text)
        # Penalise extremes: too thin to say anything, or a wall of text.
        if length < 40:
            score *= 0.6
        elif length > 2200:
            score *= 0.85
        return round(min(score, 1.0), 3)

    def _apply_learnings(self, candidate: ContentCandidate, card: ScoreCard) -> ScoreCard:
        """Let the Watchtower's past learnings gently adjust the score.

        If the Brain has learned that content with a given theme performs well (or
        badly) for trust/community, nudge accordingly — bounded so a single learning
        can never dominate the values-based score.
        """
        if not candidate.themes:
            return card
        query = " ".join(candidate.themes)
        learnings = self.brain.recall(query, kind="performance_learning", limit=3)
        if not learnings:
            return card
        nudge = 0.0
        for m in learnings:
            direction = m.metadata.get("direction", "")
            if direction == "positive":
                nudge += 0.03
            elif direction == "negative":
                nudge -= 0.03
        nudge = max(-0.06, min(0.06, nudge))
        if nudge:
            card.community_value = round(max(0.0, min(1.0, card.community_value + nudge)), 3)
            card.awareness = round(max(0.0, min(1.0, card.awareness + nudge)), 3)
        return card

    def _rationale(self, card: ScoreCard, notes: list[str]) -> str:
        top = sorted(
            card.model_dump(exclude={"rationale"}).items(),
            key=lambda kv: kv[1],
            reverse=True,
        )[:3]
        strengths = ", ".join(f"{k}={v}" for k, v in top)
        base = f"weighted={card.weighted_total()} | strengths: {strengths}"
        if notes:
            base += " | " + "; ".join(notes)
        return base
