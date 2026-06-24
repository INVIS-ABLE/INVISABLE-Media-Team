"""LLM-judge — a model-based re-scoring pass layered on the deterministic floor.

The deterministic :class:`~invisable_os.engines.scoring.Scorer` is fast and runs on
the whole field of hundreds of candidates. The judge is slower and more nuanced, so
it only re-scores the *top contenders* a tournament has already shortlisted, and its
verdict is *blended* with the deterministic score (never replaces it). This is the
classic "cheap floor + expensive judge on the shortlist" pattern.

The judge **self-disables** when no live model is configured (``available`` is
``False``), so offline behaviour is unchanged and nothing slows down in tests.
"""

from __future__ import annotations

import os

from invisable_os.config import Settings, get_settings
from invisable_os.llm import LLMClient, get_llm
from invisable_os.models.content import ContentCandidate
from invisable_os.models.scoring import SCORE_WEIGHTS, ScoreCard

JUDGE_SYSTEM = (
    "You are the Quality & Brand judge for INVISABLE®, an invisible-illness awareness "
    "movement. Score content honestly on the brand's values. Reward trust, "
    "authenticity, education, community value, awareness and warm British humour. "
    "Penalise anything that feels like clickbait, fabrication, spam, or that could "
    "damage trust. Be a tough but fair critic."
)

JUDGE_PROMPT = (
    "Rate this content on each value from 0.0 (poor) to 1.0 (excellent):\n\n"
    "HOOK: {hook}\nBODY: {body}\nCALL TO ACTION: {cta}\n\n"
    "Score: trust, community_value, authenticity, awareness, education, humour, "
    "consistency, long_term_brand. Also give a one-line 'rationale'."
)

# How much weight the judge gets when blended with the deterministic score.
JUDGE_BLEND = 0.5


def _clamp01(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


class LLMJudge:
    """Model-based scorer for shortlisted candidates."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        settings: Settings | None = None,
        *,
        force: bool = False,
    ) -> None:
        self.llm = llm or get_llm()
        self.settings = settings or get_settings()
        self._force = force

    @property
    def available(self) -> bool:
        """True only when a live model is configured — keeps offline runs untouched.

        Gated on the Claude key (env) or an explicit opt-in flag, so it never probes
        a (possibly slow) local Ollama during high-volume scoring unless asked.
        """
        return self._force or self.settings.has_claude or bool(os.getenv("INVISABLE_USE_JUDGE"))

    def score(self, candidate: ContentCandidate) -> ScoreCard | None:
        """Return the judge's ScoreCard, or ``None`` if unavailable / malformed."""
        if not self.available:
            return None
        resp = self.llm.complete_json(
            JUDGE_PROMPT.format(
                hook=candidate.hook, body=candidate.body, cta=candidate.call_to_action
            ),
            system=JUDGE_SYSTEM,
            schema_hint=", ".join(SCORE_WEIGHTS) + ", rationale",
            max_tokens=400,
        )
        if not resp.data:
            return None
        try:
            card = ScoreCard(**{dim: _clamp01(resp.data.get(dim, 0.0)) for dim in SCORE_WEIGHTS})
            card.rationale = f"judge({resp.backend}): {str(resp.data.get('rationale', '')).strip()}"
            return card
        except Exception:  # noqa: BLE001
            return None

    def blend(self, deterministic: ScoreCard, judged: ScoreCard) -> ScoreCard:
        """Blend the judge's card with the deterministic floor (bounded average)."""
        blended = ScoreCard(
            **{
                dim: round(
                    (1 - JUDGE_BLEND) * getattr(deterministic, dim)
                    + JUDGE_BLEND * getattr(judged, dim),
                    3,
                )
                for dim in SCORE_WEIGHTS
            }
        )
        blended.rationale = f"{deterministic.rationale} | {judged.rationale}"
        return blended
