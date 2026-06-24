"""Evaluation layer — one offline scorecard across every gate the platform owns.

DeepEval / Promptfoo / Ragas-style evaluation, but deterministic and offline: take
a piece of copy and run it through the whole battery at once — brand safety, the
Credible Source Rule, mission alignment, quality, humanness, and crisis care — and
get back a single scorecard with a pass/fail per metric, an overall verdict, and a
letter grade.

This is the seam an eval suite or a CI gate hooks into: ``evaluate_post`` for one
piece, ``evaluate_batch`` for a set (with the aggregate pass rate). It composes the
real engines, so the scorecard reflects exactly what the live pipeline enforces.
"""

from __future__ import annotations

from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.quality import QualityEngine
from invisable_os.guardrails import check as brand_check
from invisable_os.guardrails.crisis import crisis_review
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform
from invisable_os.services.fact_check import check_post
from invisable_os.services.humanise import humanness_score

# Mission total at/above this counts as on-mission for the scorecard.
_MISSION_THRESHOLD = 0.2
_HUMANNESS_THRESHOLD = 0.8


def _grade(rate: float) -> str:
    if rate >= 0.95:
        return "A"
    if rate >= 0.8:
        return "B"
    if rate >= 0.6:
        return "C"
    if rate >= 0.4:
        return "D"
    return "F"


def evaluate_post(
    text: str,
    *,
    sources: list[dict] | None = None,
    platform: Platform = Platform.INSTAGRAM,
    content_format: ContentFormat = ContentFormat.TEXT_POST,
    original: bool = True,
) -> dict:
    """Run the full evaluation battery over one piece of copy."""
    candidate = ContentCandidate(
        brief="evaluation",
        platform=platform,
        content_format=content_format,
        body=text,
        original=original,
    )

    verdict = brand_check(candidate)
    q = QualityEngine().score(candidate)
    m = MissionEngine().advise(candidate)
    fc = check_post(text, sources or [])
    hs = humanness_score(text)
    crisis = crisis_review(text)

    # Each metric: a 0–1 score, a pass/fail, and a human-readable detail.
    metrics = [
        {
            "name": "brand_safety",
            "score": 1.0 if verdict.passed else 0.0,
            "passed": verdict.passed,
            "detail": "passes the hard brand gate" if verdict.passed
            else f"blocked: {', '.join(verdict.reasons) or 'brand gate'}",
        },
        {
            "name": "fact_grounded",
            "score": 1.0 if fc.ok else 0.0,
            "passed": fc.ok,
            "detail": fc.advisory,
        },
        {
            "name": "mission_aligned",
            "score": round(min(1.0, m.total()), 3),
            "passed": m.total() >= _MISSION_THRESHOLD,
            "detail": f"mission verdict: {m.verdict} ({round(m.total(), 2)})",
        },
        {
            "name": "quality",
            "score": round(q.average() / 10.0, 3),
            "passed": q.passes(),
            "detail": f"quality average {round(q.average(), 1)}/10",
        },
        {
            "name": "humanness",
            "score": hs["score"],
            "passed": hs["score"] >= _HUMANNESS_THRESHOLD,
            "detail": f"{hs['tell_count']} AI tell(s)",
        },
        {
            "name": "crisis_care",
            # Non-sensitive passes outright; sensitive "passes" the eval only as a
            # flag that human approval + signposting are required (never auto-publish).
            "score": 1.0 if not crisis.sensitive else 0.0,
            "passed": not crisis.sensitive,
            "detail": "not a sensitive topic" if not crisis.sensitive
            else f"sensitive ({', '.join(crisis.topics)}) — needs human approval + signposting",
        },
    ]

    passed = sum(1 for x in metrics if x["passed"])
    total = len(metrics)
    rate = passed / total if total else 0.0
    return {
        "overall_pass": passed == total,
        "pass_rate": round(rate, 3),
        "grade": _grade(rate),
        "passed": passed,
        "total": total,
        "metrics": metrics,
        "sensitive": crisis.sensitive,
        "signposting": list(crisis.signposting) if crisis.sensitive else [],
    }


def evaluate_batch(items, *, platform: Platform = Platform.INSTAGRAM) -> dict:
    """Evaluate a set of pieces and report the aggregate pass rate.

    ``items`` may be a list of strings or of dicts. A dict may carry ``text`` plus
    any of ``sources`` / ``platform`` / ``content_format`` to override per item.
    """
    results: list[dict] = []
    for it in items or []:
        if isinstance(it, dict):
            text = it.get("text", "")
            plat = it.get("platform", platform)
            if isinstance(plat, str):
                plat = Platform(plat)
            fmt = it.get("content_format", ContentFormat.TEXT_POST)
            if isinstance(fmt, str):
                fmt = ContentFormat(fmt)
            results.append(
                evaluate_post(text, sources=it.get("sources"), platform=plat,
                              content_format=fmt)
            )
        else:
            results.append(evaluate_post(it, platform=platform))

    n = len(results)
    fully = sum(1 for r in results if r["overall_pass"])
    avg = round(sum(r["pass_rate"] for r in results) / n, 3) if n else 0.0
    return {
        "count": n,
        "fully_passing": fully,
        "avg_pass_rate": avg,
        "grade": _grade(avg),
        "results": results,
    }
