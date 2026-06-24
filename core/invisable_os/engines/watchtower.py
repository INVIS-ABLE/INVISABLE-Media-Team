"""Algorithm Watchtower.

Monitors how published content actually performs and feeds the learning back into
``INVISABLE_BRAIN`` so the Scorer (and therefore future tournaments) gets smarter.

It also computes the **Founder Recognition Index** — a composite of the
recognition-bearing success metrics (media mentions, podcast invitations, speaking
and partner/sponsor enquiries, profile visits) — because the directive treats
founder recognition as a first-class success metric and a *consequence of impact*.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from invisable_os.brain import Memory, get_brain
from invisable_os.models.metrics import PerformanceSignal, SuccessMetric

# Metrics that, taken together, express founder recognition. Weights sum to 1.0.
FOUNDER_RECOGNITION_METRICS: dict[SuccessMetric, float] = {
    SuccessMetric.MEDIA_MENTIONS: 0.25,
    SuccessMetric.PODCAST_INVITATIONS: 0.20,
    SuccessMetric.SPEAKING_OPPORTUNITIES: 0.20,
    SuccessMetric.PARTNER_ENQUIRIES: 0.12,
    SuccessMetric.SPONSOR_ENQUIRIES: 0.12,
    SuccessMetric.PROFILE_VISITS: 0.11,
}


@dataclass
class WatchtowerReport:
    totals: dict[str, float] = field(default_factory=dict)
    founder_recognition_index: float = 0.0
    learnings: list[str] = field(default_factory=list)


class AlgorithmWatchtower:
    """Ingests performance signals, learns, and computes recognition indices."""

    def __init__(self) -> None:
        self.brain = get_brain()

    def ingest(self, signals: list[PerformanceSignal]) -> WatchtowerReport:
        """Process a batch of signals into learnings + a report."""
        totals: dict[str, float] = defaultdict(float)
        by_theme_metric: dict[tuple[str, str], list[float]] = defaultdict(list)

        for s in signals:
            totals[s.metric.value] += s.value
            for theme in s.themes or ["uncategorised"]:
                by_theme_metric[(theme, s.metric.value)].append(s.value)

        learnings: list[str] = []
        for (theme, metric), values in by_theme_metric.items():
            avg = sum(values) / len(values)
            # Heuristic threshold for "this theme is resonating" — relative to engagement
            # metrics that the community genuinely values (saves, shares, submissions).
            if metric in {
                SuccessMetric.SAVES.value,
                SuccessMetric.SHARES.value,
                SuccessMetric.STORY_SUBMISSIONS.value,
            } and avg > 0:
                direction = "positive"
                learnings.append(
                    f"Theme '{theme}' drives {metric} (avg {avg:.1f}) — favour it."
                )
                self.brain.remember(
                    Memory(
                        text=f"Theme '{theme}' performs well on {metric} (avg {avg:.1f}).",
                        kind="performance_learning",
                        metadata={"theme": theme, "metric": metric, "direction": direction},
                    )
                )

        fri = self.founder_recognition_index(dict(totals))
        return WatchtowerReport(
            totals=dict(totals), founder_recognition_index=fri, learnings=learnings
        )

    def attribute_recognition(self, signals: list) -> list[dict]:
        """Split the Founder Recognition Index across the posts that earned it.

        The index is a saturating, non-linear function of *aggregate* recognition
        metrics, so a post's contribution isn't simply its raw numbers. We compute
        each recognition metric's contribution to the index, then allocate that
        contribution to posts in proportion to their share of the metric. The result
        is exact — the per-post contributions sum back to the index — and explainable:
        each post carries a per-metric breakdown ("podcast invitations: 0.15").

        ``signals`` may be :class:`PerformanceSignal` objects or plain dicts with
        ``candidate_id`` / ``metric`` / ``value`` keys (as the store returns them).
        Returns posts ranked by contribution, highest first.
        """
        recognition = {m.value for m in FOUNDER_RECOGNITION_METRICS}
        metric_totals: dict[str, float] = defaultdict(float)
        by_post: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for s in signals:
            metric = s["metric"] if isinstance(s, dict) else s.metric.value
            if metric not in recognition:
                continue
            cid = s["candidate_id"] if isinstance(s, dict) else s.candidate_id
            value = float(s["value"] if isinstance(s, dict) else s.value)
            metric_totals[metric] += value
            by_post[cid][metric] += value

        # Each recognition metric's (saturated, weighted) contribution to the index.
        metric_contribution: dict[str, float] = {}
        for metric_enum, weight in FOUNDER_RECOGNITION_METRICS.items():
            metric = metric_enum.value
            total = metric_totals.get(metric, 0.0)
            ref = _REFERENCE.get(metric_enum, 10.0)
            saturated = total / (total + ref) if total > 0 else 0.0
            metric_contribution[metric] = weight * saturated

        posts: list[dict] = []
        for cid, metrics in by_post.items():
            breakdown: dict[str, float] = {}
            for metric, value in metrics.items():
                total = metric_totals[metric]
                share = value / total if total > 0 else 0.0
                contrib = round(metric_contribution.get(metric, 0.0) * share, 4)
                if contrib > 0:
                    breakdown[metric] = contrib
            posts.append({
                "candidate_id": cid,
                "contribution": round(sum(breakdown.values()), 4),
                "breakdown": breakdown,
                "metrics": {k: round(v, 2) for k, v in metrics.items()},
            })
        posts.sort(key=lambda p: p["contribution"], reverse=True)
        return posts

    def founder_recognition_index(self, totals: dict[str, float]) -> float:
        """Composite 0+ index of founder recognition from recognition-bearing metrics.

        Uses a saturating transform per metric so a single spike can't dominate; the
        index is comparable across periods and is what the platform tries to grow as a
        consequence of genuine impact.
        """
        index = 0.0
        for metric, weight in FOUNDER_RECOGNITION_METRICS.items():
            value = totals.get(metric.value, 0.0)
            # Saturating: diminishing returns above a soft reference point.
            ref = _REFERENCE.get(metric, 10.0)
            saturated = value / (value + ref) if value > 0 else 0.0
            index += weight * saturated
        return round(index, 4)


# Soft reference points for saturation (per reporting period). Tunable as the
# movement grows; chosen so early wins move the needle meaningfully.
_REFERENCE: dict[SuccessMetric, float] = {
    SuccessMetric.MEDIA_MENTIONS: 5.0,
    SuccessMetric.PODCAST_INVITATIONS: 3.0,
    SuccessMetric.SPEAKING_OPPORTUNITIES: 3.0,
    SuccessMetric.PARTNER_ENQUIRIES: 8.0,
    SuccessMetric.SPONSOR_ENQUIRIES: 8.0,
    SuccessMetric.PROFILE_VISITS: 2000.0,
}
