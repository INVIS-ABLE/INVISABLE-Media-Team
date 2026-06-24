"""Newsroom Mode — turn a breaking item into source-grounded, gated angles, fast.

When something lands in the news the trades or the invisible-illness community
care about, speed matters — but never at the cost of the [Credible Source Rule].
Newsroom Mode takes a headline and its source and, in one call, drafts a spread of
angles (founder reaction · explainer · solidarity · myth-vs-reality), grounds each
in the supplied source, and runs the whole lot through the platform's hard gates.

It is honest about readiness: a fact-led angle with no credible source behind it
is flagged ``source_required`` and held for review rather than shipped as a rumour.
A sensitive headline is routed through [Crisis Mode] first. Everything runs offline.
"""

from __future__ import annotations

import uuid

from invisable_os.engines.generator import Generator
from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.quality import QualityEngine
from invisable_os.guardrails import check as brand_check
from invisable_os.guardrails.crisis import crisis_review
from invisable_os.models.content import Platform, QueueStatus
from invisable_os.services.fact_check import (
    MAX_TIER_FOR_FACTS,
    attribution_line,
    check_post,
    credibility,
)
from invisable_os.store import Repository, get_repository

# The rapid-response spread: a reaction, an explainer, a show of solidarity, and a
# myth-buster. Each entry is (generator angle, content pillar).
NEWSROOM_ANGLES: list[tuple[str, str]] = [
    ("founder_voice", "founder"),
    ("explainer", "education"),
    ("solidarity", "community"),
    ("myth_vs_reality", "trends"),
]

_DEFAULT_ANGLES = len(NEWSROOM_ANGLES)
_MAX_ANGLES = 12


def newsroom_brief(
    headline: str,
    *,
    summary: str = "",
    source_name: str = "",
    source_url: str = "",
    source_type: str = "news",
    platform: Platform = Platform.TIKTOK,
    count: int = _DEFAULT_ANGLES,
    persist: bool = False,
    repository: Repository | None = None,
) -> dict:
    """Draft a spread of gated, source-grounded angles for a breaking item."""
    repo = repository or get_repository()
    count = max(1, min(count, _MAX_ANGLES))
    headline = headline.strip()
    brief = f"{headline}. {summary}".strip()

    # 1. CARE FIRST — a sensitive headline is routed through Crisis Mode.
    crisis = crisis_review(brief)

    # 2. ASSESS THE SOURCE — is it strong enough to back a hard fact?
    tier, label = credibility(source_type)
    credible_for_facts = tier <= MAX_TIER_FOR_FACTS
    source = (
        {"name": source_name or label, "url": source_url, "source_type": source_type}
        if (source_name or source_url)
        else None
    )
    sources = [source] if source else []

    # 3. GENERATE + GATE — one angle at a time, grounded in the source.
    generator = Generator()
    quality = QualityEngine()
    mission = MissionEngine()
    newsroom_id = uuid.uuid4().hex

    angles: list[dict] = []
    for i in range(count):
        angle, pillar = NEWSROOM_ANGLES[i % len(NEWSROOM_ANGLES)]
        cand = generator.generate(brief, platform, count=1, angle=angle)[0]
        cand.themes = [*(cand.themes or []), pillar]
        verdict = brand_check(cand)
        q = quality.score(cand)
        m = mission.advise(cand)
        fc = check_post(cand.full_text, sources)
        flagged = bool(verdict.needs_human_review) or not fc.ok or crisis.sensitive
        angles.append(
            {
                "angle": angle,
                "pillar": pillar,
                "candidate": cand.model_dump(),
                "brand_passed": verdict.passed,
                "quality_avg": q.average(),
                "quality_passes": q.passes(),
                "mission_total": m.total(),
                "mission_verdict": m.verdict,
                "fact_ok": fc.ok,
                "fact_led": fc.fact_led,
                "needs_review": flagged,
                "attribution": fc.attributions[0] if fc.attributions else "",
            }
        )

    usable = [a for a in angles if a["brand_passed"]]
    source_required = any(a["fact_led"] and not a["fact_ok"] for a in angles)

    guidance: list[str] = []
    if crisis.sensitive:
        guidance.append(
            "Sensitive topic — human approval + signposting required before publishing."
        )
    if source_required:
        guidance.append(
            "Some angles are fact-led with no credible source — attach an official/credible "
            "source before approval, never ship an unsourced claim."
        )
    if source and not credible_for_facts:
        guidance.append(
            f"The supplied source ({label}, tier {tier}) is too weak to back a hard fact."
        )
    if not guidance:
        guidance.append("Source-grounded and clean — ready for human approval.")

    queued_ids: list[str] = []
    if persist:
        queued_ids = _enqueue(repo, usable, newsroom_id, platform, source)

    return {
        "newsroom_id": newsroom_id,
        "headline": headline,
        "platform": platform.value,
        "source": {
            "name": source_name or (label if source else ""),
            "url": source_url,
            "source_type": source_type,
            "tier": tier,
            "credible_for_facts": credible_for_facts,
        },
        "crisis": crisis.as_dict(),
        "angles": angles,
        "funnel": {
            "raw": len(angles),
            "brand_passed": len(usable),
            "brand_rejected": len(angles) - len(usable),
            "needs_review": sum(1 for a in angles if a["needs_review"]),
        },
        "source_required": source_required,
        "publish_ready": not source_required and not crisis.sensitive and bool(usable),
        "guidance": guidance,
        "persisted": persist,
        "queued_ids": queued_ids,
    }


def _enqueue(repo: Repository, usable: list[dict], newsroom_id: str,
             platform: Platform, source: dict | None) -> list[str]:
    ids: list[str] = []
    attribution = attribution_line(source) if source else ""
    for a in usable:
        cand = dict(a["candidate"])
        tags = list(cand.get("tags") or [])
        tag = f"newsroom:{newsroom_id}"
        if tag not in tags:
            tags.append(tag)
        cand["tags"] = tags
        if attribution:
            cand["attribution"] = attribution
        queue_id = repo.enqueue(
            {
                "candidate_id": cand.get("id", ""),
                "candidate": cand,
                "status": QueueStatus.PENDING_REVIEW.value,
                "pillar": a["pillar"],
                "platform": platform.value,
                "quality_avg": a["quality_avg"],
                "quality_passes": a["quality_passes"],
                "mission_total": a["mission_total"],
                "mission_verdict": a["mission_verdict"],
                "needs_human_review": a["needs_review"],
                "tags": tags,
            }
        )
        ids.append(queue_id)
    return ids
