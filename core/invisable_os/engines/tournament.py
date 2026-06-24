"""Content Tournament Engine.

The directive: *generate hundreds of candidates daily, then score, improve, rank,
and select only the highest-quality outputs.*

The pipeline:

    generate  →  GUARDRAIL (hard gate)  →  score  →  improve (top contenders)
              →  re-score  →  rank  →  select  →  remember winners

Guardrails run first and are absolute: a blocked candidate is out, no matter how
high it might otherwise score. Selection is then a pure ranking on the values-
weighted composite, with the Founder Engine rebalancing the final set toward the
~80% founder-presence target.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invisable_os.brain import Memory, get_brain
from invisable_os.engines.founder import FounderEngine
from invisable_os.engines.generator import Generator
from invisable_os.engines.scoring import Scorer
from invisable_os.guardrails import check
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform
from invisable_os.models.scoring import ScoredCandidate


@dataclass
class TournamentResult:
    """The outcome of one tournament run."""

    brief: str
    platform: Platform
    generated: int
    blocked: int
    winners: list[ScoredCandidate] = field(default_factory=list)
    shortlist: list[ScoredCandidate] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "brief": self.brief,
            "platform": self.platform.value,
            "generated": self.generated,
            "blocked_by_guardrails": self.blocked,
            "selected": len(self.winners),
            "winners": [
                {
                    "id": w.candidate.id,
                    "hook": w.candidate.hook,
                    "total": w.total,
                    "founder_centred": w.candidate.founder_centred,
                    "improvement_passes": w.improvement_passes,
                    "rationale": w.scorecard.rationale,
                }
                for w in self.winners
            ],
        }


class ContentTournamentEngine:
    """Runs the generate → gate → score → improve → rank → select pipeline."""

    def __init__(
        self,
        generator: Generator | None = None,
        scorer: Scorer | None = None,
        founder: FounderEngine | None = None,
    ) -> None:
        self.generator = generator or Generator()
        self.scorer = scorer or Scorer()
        self.founder = founder or FounderEngine()
        self.brain = get_brain()

    def run(
        self,
        brief: str,
        platform: Platform = Platform.INSTAGRAM,
        *,
        count: int = 24,
        select: int = 3,
        content_format: ContentFormat = ContentFormat.SHORT_VIDEO,
        improve_top: int = 6,
        published: list[ContentCandidate] | None = None,
    ) -> TournamentResult:
        """Execute one tournament and return the winners."""
        # 1. Generate the field.
        field_ = self.generator.generate(
            brief, platform, count=count, content_format=content_format
        )

        # 2. Hard gate + initial score. A blocked candidate is still recorded (as a
        #    zero) but can never be selected.
        scored: list[ScoredCandidate] = []
        blocked = 0
        for candidate in field_:
            verdict = check(candidate)
            if verdict.blocked:
                blocked += 1
            scored.append(
                ScoredCandidate(
                    candidate=candidate,
                    guardrail=verdict,
                    scorecard=self.scorer.score(candidate),
                )
            )

        # 3. Improve the top contenders, then re-score.
        passable = sorted(
            (s for s in scored if not s.guardrail.blocked),
            key=lambda s: s.total,
            reverse=True,
        )
        for sc in passable[:improve_top]:
            self._improve(sc)

        # 4. Rank (recompute order after improvement), de-duplicating identical text
        #    so the winners are genuinely distinct rather than near-clones.
        ranked_all = sorted(
            (s for s in scored if not s.guardrail.blocked), key=lambda s: s.total, reverse=True
        )
        ranked = self._dedupe(ranked_all)

        # 5. Select, then let the Founder Engine rebalance toward the target mix.
        chosen = ranked[: max(select, 0)]
        rebalanced_candidates = self.founder.rebalance(
            [s.candidate for s in chosen], published=published
        )
        order = {c.id: i for i, c in enumerate(rebalanced_candidates)}
        chosen.sort(key=lambda s: order.get(s.candidate.id, 999))

        # 6. Remember the winners so the platform compounds what works.
        for w in chosen:
            self._remember_winner(w)

        return TournamentResult(
            brief=brief,
            platform=platform,
            generated=len(field_),
            blocked=blocked,
            winners=chosen,
            shortlist=ranked[: max(select * 3, select)],
        )

    @staticmethod
    def _dedupe(ranked: list[ScoredCandidate]) -> list[ScoredCandidate]:
        """Keep the highest-scoring instance of each distinct piece of text."""
        seen: set[str] = set()
        unique: list[ScoredCandidate] = []
        for sc in ranked:
            key = sc.candidate.full_text.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(sc)
        return unique

    def _improve(self, scored: ScoredCandidate) -> None:
        """Apply one improvement pass to a contender, re-gating and re-scoring.

        Improvement targets the weakest dimension. Offline this is a light,
        deterministic strengthening of structure (e.g. ensuring a CTA exists); with a
        live model it would rewrite toward the weakest value. It always re-runs the
        guardrails so an improvement can never sneak past the hard gate.
        """
        card = scored.scorecard
        weakest = min(
            card.model_dump(exclude={"rationale"}).items(), key=lambda kv: kv[1]
        )[0]
        cand = scored.candidate

        if weakest == "consistency" and not cand.call_to_action.strip():
            cand.call_to_action = "If this resonates, share it with someone who needs to see it."
        elif weakest == "community_value" and "you're not alone" not in cand.body.lower():
            cand.body = (cand.body + " You're not alone in this.").strip()
        elif weakest == "education" and "because" not in cand.body.lower():
            cand.body = (cand.body + " It matters because being unseen is exhausting.").strip()

        # Re-gate and re-score after the edit.
        scored.guardrail = check(cand)
        scored.scorecard = self.scorer.score(cand)
        scored.improvement_passes += 1

    def _remember_winner(self, winner: ScoredCandidate) -> None:
        self.brain.remember(
            Memory(
                text=f"WINNER ({winner.total}): {winner.candidate.hook} — {winner.candidate.body}",
                kind="winning_pattern",
                metadata={
                    "platform": winner.candidate.platform.value,
                    "themes": ",".join(winner.candidate.themes),
                    "founder_centred": winner.candidate.founder_centred,
                    "total": winner.total,
                },
            )
        )
