"""Format Split Testing — try one idea in several formats, learn which one lands.

The same brief rarely performs the same as a punchy short video, a swipe-through
carousel, a single image, or a plain text post. This builds a *split*: one gated
variant of an idea per format, tagged as one experiment, so the founder can put
them out head-to-head. Once performance signals come back, ``format_leaderboard``
aggregates them by format and recommends the winner.

It is deterministic and offline: the generator degrades to templates, the gates
are the real hard-gate code, and the leaderboard is plain arithmetic over the
signals the Watchtower already records.
"""

from __future__ import annotations

import uuid

from invisable_os.engines.generator import Generator
from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.quality import QualityEngine
from invisable_os.guardrails import check as brand_check
from invisable_os.models.content import ContentFormat, Platform, QueueStatus
from invisable_os.services.fact_check import check_post
from invisable_os.store import Repository, get_repository

# A sensible default spread: the four formats most ideas can take, across the
# video / swipe / still / words divide.
DEFAULT_SPLIT_FORMATS: list[ContentFormat] = [
    ContentFormat.SHORT_VIDEO,
    ContentFormat.CAROUSEL,
    ContentFormat.IMAGE,
    ContentFormat.TEXT_POST,
]

_MIN_SAMPLES = 3  # below this, a format's average isn't trustworthy yet


def _gate_one(cand, quality: QualityEngine, mission: MissionEngine) -> dict:
    """Run a single candidate through the same hard gates the swarm uses."""
    verdict = brand_check(cand)
    q = quality.score(cand)
    fc = check_post(cand.full_text, [])  # no source attached at draft time
    m = mission.advise(cand)
    return {
        "format": cand.content_format.value,
        "candidate": cand.model_dump(),
        "brand_passed": verdict.passed,
        "quality_avg": q.average(),
        "quality_passes": q.passes(),
        "mission_total": m.total(),
        "mission_verdict": m.verdict,
        "fact_ok": fc.ok,
        "needs_review": bool(verdict.needs_human_review) or not fc.ok,
    }


def build_split(
    brief: str,
    *,
    formats: list[ContentFormat] | None = None,
    platform: Platform = Platform.TIKTOK,
    persist: bool = False,
    repository: Repository | None = None,
) -> dict:
    """Generate one gated variant of ``brief`` per format, as one experiment."""
    repo = repository or get_repository()
    # De-dupe while preserving order; fall back to the default spread.
    chosen: list[ContentFormat] = []
    for fmt in formats or DEFAULT_SPLIT_FORMATS:
        if fmt not in chosen:
            chosen.append(fmt)

    generator = Generator()
    quality = QualityEngine()
    mission = MissionEngine()
    experiment_id = uuid.uuid4().hex

    variants: list[dict] = []
    for fmt in chosen:
        cand = generator.generate(brief, platform, count=1, content_format=fmt)[0]
        variants.append(_gate_one(cand, quality, mission))

    usable = [v for v in variants if v["brand_passed"]]
    queued_ids: list[str] = []
    if persist:
        queued_ids = _enqueue(repo, usable, experiment_id, platform)

    return {
        "experiment_id": experiment_id,
        "brief": brief,
        "platform": platform.value,
        "formats": [f.value for f in chosen],
        "variants": variants,
        "funnel": {
            "raw": len(variants),
            "brand_passed": len(usable),
            "brand_rejected": len(variants) - len(usable),
            "needs_review": sum(1 for v in variants if v["needs_review"]),
        },
        "persisted": persist,
        "queued_ids": queued_ids,
    }


def _enqueue(repo: Repository, usable: list[dict], experiment_id: str,
             platform: Platform) -> list[str]:
    ids: list[str] = []
    for v in usable:
        cand = dict(v["candidate"])
        tags = list(cand.get("tags") or [])
        for tag in (f"split:{experiment_id}", f"format:{v['format']}"):
            if tag not in tags:
                tags.append(tag)
        cand["tags"] = tags
        queue_id = repo.enqueue(
            {
                "candidate_id": cand.get("id", ""),
                "candidate": cand,
                "status": QueueStatus.PENDING_REVIEW.value,
                "platform": platform.value,
                "quality_avg": v["quality_avg"],
                "quality_passes": v["quality_passes"],
                "mission_total": v["mission_total"],
                "mission_verdict": v["mission_verdict"],
                "needs_human_review": v["needs_review"],
                "tags": tags,
            }
        )
        ids.append(queue_id)
    return ids


def format_leaderboard(
    *,
    repository: Repository | None = None,
    metric: str | None = None,
    min_samples: int = _MIN_SAMPLES,
) -> dict:
    """Rank content formats by their recorded performance and recommend a winner.

    Joins the Watchtower's performance signals to the format of the post they
    belong to (via the approval queue), averages per format, and recommends the
    best format that has at least ``min_samples`` signals behind it.
    """
    repo = repository or get_repository()

    # candidate_id → the format that candidate was published in.
    fmt_by_candidate: dict[str, str] = {}
    for item in repo.list_queue(limit=100_000):
        cand_id = item.get("candidate_id")
        fmt = (item.get("candidate") or {}).get("content_format")
        if cand_id and fmt:
            fmt_by_candidate[cand_id] = fmt

    totals: dict[str, dict] = {}
    for sig in repo.list_signals():
        if metric and sig.get("metric") != metric:
            continue
        fmt = fmt_by_candidate.get(sig.get("candidate_id"))
        if not fmt:
            continue
        bucket = totals.setdefault(fmt, {"samples": 0, "total_value": 0.0})
        bucket["samples"] += 1
        bucket["total_value"] += float(sig.get("value", 0.0))

    by_format = [
        {
            "format": fmt,
            "samples": b["samples"],
            "total_value": round(b["total_value"], 3),
            "avg_value": round(b["total_value"] / b["samples"], 3) if b["samples"] else 0.0,
        }
        for fmt, b in totals.items()
    ]
    by_format.sort(key=lambda r: r["avg_value"], reverse=True)

    confident = [r for r in by_format if r["samples"] >= min_samples]
    recommended = confident[0]["format"] if confident else None

    return {
        "metric": metric or "all",
        "min_samples": min_samples,
        "by_format": by_format,
        "recommended": recommended,
        "confident": bool(confident),
    }
