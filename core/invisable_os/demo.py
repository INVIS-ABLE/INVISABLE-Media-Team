"""A runnable demonstration of the whole platform in one cycle.

    python -m invisable_os.demo

Runs offline (no keys, no services) using the deterministic fallbacks, so it always
works and shows the engines cooperating: harvest → tournament (gate/score/improve/
rank/select/rebalance) → community comment → watchtower learning → recognition index.
"""

from __future__ import annotations

import logging

from invisable_os.engines import (
    AlgorithmWatchtower,
    CommunityEngagement,
    IntelligenceHarvester,
)
from invisable_os.engines.tournament import ContentTournamentEngine
from invisable_os.guardrails.policy import PRIME_DIRECTIVE
from invisable_os.models.content import Platform
from invisable_os.models.metrics import PerformanceSignal, SuccessMetric


def _rule(title: str) -> None:
    print(f"\n{'─' * 4} {title} {'─' * (60 - len(title))}")


def main() -> None:
    logging.disable(logging.INFO)
    print("INVISABLE® AI Media Agency OS — demo cycle")
    print("Prime Directive:", PRIME_DIRECTIVE)

    _rule("1. Harvest abstracted public signals")
    signals = IntelligenceHarvester().harvest(
        ["invisible illness", "chronic fatigue", "trades mental health"]
    )
    for s in signals:
        print(f"  • [{s.kind}] {s.topic} — {s.summary[:70]}…")

    _rule("2. Content Tournament (generate → gate → score → improve → select)")
    result = ContentTournamentEngine().run(
        "Explain that fatigue in invisible illness is not laziness",
        Platform.INSTAGRAM,
        count=120,
        select=5,
    )
    print(f"  generated={result.generated}  blocked_by_guardrails={result.blocked}  "
          f"selected={len(result.winners)}")
    for w in result.winners:
        tag = "FOUNDER" if w.candidate.founder_centred else "       "
        print(f"  • {w.total:.3f} {tag} | {w.candidate.hook[:55]}")

    _rule("3. Community engagement (compliant comment)")
    draft = CommunityEngagement().draft_comment(
        "A creator opening up about their chronic fatigue journey."
    )
    print(f"  approved={draft.approved} | {draft.text}")

    _rule("4. Watchtower learns + Founder Recognition Index")
    report = AlgorithmWatchtower().ingest(
        [
            PerformanceSignal(candidate_id="c1", platform="instagram",
                              metric=SuccessMetric.SAVES, value=320, themes=["explainer"]),
            PerformanceSignal(candidate_id="c1", platform="instagram",
                              metric=SuccessMetric.MEDIA_MENTIONS, value=4),
            PerformanceSignal(candidate_id="c2", platform="instagram",
                              metric=SuccessMetric.PODCAST_INVITATIONS, value=2),
        ]
    )
    for learning in report.learnings:
        print(f"  • learned: {learning}")
    print(f"  Founder Recognition Index: {report.founder_recognition_index}")

    print("\nDone. Every external dependency degraded gracefully — no keys required.")


if __name__ == "__main__":
    main()
