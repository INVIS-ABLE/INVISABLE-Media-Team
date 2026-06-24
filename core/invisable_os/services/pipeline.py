"""Pipeline service — run the day's plan and persist it into the approval queue.

This is the seam that makes the Daily Output System *operational*: each planned post
becomes a durable queue item with its scores, tags, and flywheel assets, ready for
human approval in the PWA.
"""

from __future__ import annotations

from invisable_os.engines.daily import DailyContentDirector, PlannedPost
from invisable_os.engines.tagging import TagNetwork
from invisable_os.models.content import QueueStatus
from invisable_os.store import Repository, get_repository


def _queue_item_from(post: PlannedPost, tags: list[str]) -> dict:
    # Below the quality bar → route to NEEDS_IMPROVEMENT, else PENDING_REVIEW.
    status = (
        QueueStatus.NEEDS_IMPROVEMENT.value
        if post.needs_improvement
        else QueueStatus.PENDING_REVIEW.value
    )
    return {
        "id": post.candidate.id,
        "candidate_id": post.candidate.id,
        "candidate": post.candidate.model_dump(),
        "status": status,
        "slot_label": post.slot_label,
        "pillar": post.pillar,
        "platform": post.candidate.platform.value,
        "weighted_total": round(post.quality.average() / 10.0, 4),
        "mission_total": post.mission.total(),
        "mission_verdict": post.mission.verdict,
        "quality_avg": post.quality.average(),
        "quality_passes": post.quality.passes(),
        "needs_human_review": post.needs_human_review,
        "risk_flags": [],
        "tags": tags,
        "asset_count": len(post.flywheel),
        "flywheel": [a.kind for a in post.flywheel.assets],
    }


def persist_plan(
    posts: list[PlannedPost],
    *,
    repository: Repository | None = None,
    tag_network: TagNetwork | None = None,
) -> list[str]:
    """Persist planned posts into the queue; returns the new queue-item ids."""
    repo = repository or get_repository()
    net = tag_network or TagNetwork(repo.list_tag_members())
    ids: list[str] = []
    for post in posts:
        platform = post.candidate.platform
        try:
            tags = net.select(platform).handles
        except Exception:  # noqa: BLE001 — tagging must never block queueing
            tags = []
        ids.append(repo.enqueue(_queue_item_from(post, tags)))
    return ids


def run_and_queue_daily(
    *,
    candidates_per_slot: int = 16,
    director: DailyContentDirector | None = None,
    repository: Repository | None = None,
) -> dict:
    """Run the full day and persist it. Returns the plan summary + queue ids."""
    director = director or DailyContentDirector()
    plan = director.plan_day(candidates_per_slot=candidates_per_slot)
    ids = persist_plan(plan.posts, repository=repository)
    summary = plan.summary()
    summary["queued_ids"] = ids
    return summary
