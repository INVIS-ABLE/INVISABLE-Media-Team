"""Content War Chest service — the reserve that lets the platform post at scale.

The platform's rule is **always generate more than you publish**. The War Chest is
the durable reserve that makes that real:

* :func:`stock_approved` moves approved queue items into the reserve, classifying
  each by category, copying its scores, and stamping freshness + an expiry horizon.
* :func:`reserve_health` reports the reserve tier (below-minimum / minimum / healthy
  / elite) against the 500 / 1,000 / 2,000 thresholds and recommends a daily posting
  cadence — strong reserve → post more; thin reserve → protect it and post fewer.
* :func:`select_next` draws the best *non-repetitive* item for the next slot: it
  scores on quality, mission, freshness and humour, rotates categories so two
  consecutive posts never feel identical, and marks the chosen item used.

Everything is deterministic and offline-testable, in keeping with the rest of the
platform.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from invisable_os.models.content import QueueStatus
from invisable_os.store import Repository, get_repository

# Reserve health thresholds (count of ``ready`` items). From the V3 spec.
RESERVE_MINIMUM = 500
RESERVE_HEALTHY = 1_000
RESERVE_ELITE = 2_000

# Recommended posts/day per tier (spec cadence: 48 default · 72 target · 96 max;
# below minimum we protect the reserve and post fewer — quality over quantity).
_CADENCE_BY_TIER = {
    "below_minimum": 24,
    "minimum": 48,
    "healthy": 72,
    "elite": 96,
}

# Topical pillars age out; evergreen pillars are timeless. Drives expiry + category.
_EVERGREEN_PILLARS = {"humour", "education", "community", "founder"}
_TOPICAL_HORIZON_DAYS = 30
_EVERGREEN_HORIZON_DAYS = 180


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


# --- stocking ---------------------------------------------------------------


def stock_approved(*, repository: Repository | None = None, limit: int = 1000) -> dict:
    """Stock every approved queue item into the War Chest (idempotently).

    Returns a small summary: how many were stocked and the new reserve counts.
    """
    repo = repository or get_repository()
    approved = repo.list_queue(status=QueueStatus.APPROVED.value, limit=limit)
    stocked = 0
    for item in approved:
        if repo.war_chest_has_queue_item(item["id"]):
            continue
        repo.add_war_chest_item(_item_from_queue(item))
        stocked += 1
    return {"stocked": stocked, "counts": repo.war_chest_counts()}


def _item_from_queue(item: dict) -> dict:
    """Map an approval-queue item into a War Chest reserve record."""
    candidate = item.get("candidate") or {}
    pillar = (item.get("pillar") or "evergreen").lower()
    evergreen = pillar in _EVERGREEN_PILLARS
    horizon = _EVERGREEN_HORIZON_DAYS if evergreen else _TOPICAL_HORIZON_DAYS
    title = candidate.get("hook") or candidate.get("brief") or item.get("pillar") or "(untitled)"
    return {
        "queue_item_id": item["id"],
        "candidate_id": item.get("candidate_id", ""),
        "title": title[:200],
        "category": pillar or "evergreen",
        "platform": item.get("platform", ""),
        "pillar": pillar,
        "evergreen": evergreen,
        "reserve_status": "ready",
        "quality_score": item.get("quality_avg", 0.0),
        "mission_score": item.get("mission_total", 0.0),
        "humour_score": float((candidate.get("scores") or {}).get("humour", 0.0)),
        "risk_score": 1.0 if item.get("risk_flags") else 0.0,
        "freshness_score": 1.0,
        "tags": item.get("tags", []),
        "payload": candidate,
        "expiry_date": _now() + timedelta(days=horizon),
    }


# --- reserve health ---------------------------------------------------------


def reserve_tier(ready: int) -> str:
    if ready >= RESERVE_ELITE:
        return "elite"
    if ready >= RESERVE_HEALTHY:
        return "healthy"
    if ready >= RESERVE_MINIMUM:
        return "minimum"
    return "below_minimum"


def reserve_health(*, repository: Repository | None = None) -> dict:
    """Report the reserve level, tier, recommended cadence and category spread."""
    repo = repository or get_repository()
    counts = repo.war_chest_counts()
    ready = counts["ready"]
    tier = reserve_tier(ready)
    recommended = _CADENCE_BY_TIER[tier]
    # Fraction of the way to the next milestone, for a progress meter.
    if tier == "elite":
        progress = 1.0
    else:
        target = {"below_minimum": RESERVE_MINIMUM, "minimum": RESERVE_HEALTHY,
                  "healthy": RESERVE_ELITE}[tier]
        progress = round(min(1.0, ready / target), 3)
    return {
        "ready": ready,
        "tier": tier,
        "thresholds": {
            "minimum": RESERVE_MINIMUM,
            "healthy": RESERVE_HEALTHY,
            "elite": RESERVE_ELITE,
        },
        "progress_to_next": progress,
        "recommended_posts_per_day": recommended,
        "recommended_interval_minutes": round(24 * 60 / recommended) if recommended else 0,
        "by_category": counts["by_category"],
        "by_status": counts["by_status"],
        "always_generate_more_than_published": True,
    }


# --- selection (anti-repetition) -------------------------------------------


def _freshness(item: dict, now: datetime) -> float:
    """Recompute freshness from age vs. the item's expiry horizon (0–1)."""
    created = item.get("created_at")
    expiry = item.get("expiry_date")
    if not created:
        return float(item.get("freshness_score", 1.0))
    created_dt = _as_utc(datetime.fromisoformat(created))
    age_days = max(0.0, (now - created_dt).total_seconds() / 86_400)
    if expiry:
        span = _as_utc(datetime.fromisoformat(expiry)) - created_dt
        horizon = max(1.0, span.total_seconds() / 86_400)
    else:
        horizon = float(_EVERGREEN_HORIZON_DAYS)
    return round(max(0.0, 1.0 - age_days / horizon), 3)


def _score(item: dict, now: datetime, *, avoid_category: str | None) -> float:
    """Rank a reserve item: quality + mission + freshness + humour − risk, with a
    penalty for repeating the most-recently-used category."""
    quality = float(item.get("quality_score", 0.0)) / 10.0  # quality is on a /10 scale
    mission = float(item.get("mission_score", 0.0))
    humour = float(item.get("humour_score", 0.0))
    risk = float(item.get("risk_score", 0.0))
    fresh = _freshness(item, now)
    base = 0.45 * quality + 0.30 * mission + 0.15 * fresh + 0.10 * humour
    base -= 0.5 * risk
    base -= 0.10 * (item.get("reuse_count") or 0)  # prefer never-used items
    if avoid_category and item.get("category") == avoid_category:
        base -= 0.25  # rotate categories so consecutive posts don't feel identical
    return base


def select_next(
    *,
    repository: Repository | None = None,
    platform: str | None = None,
    category: str | None = None,
    mark_used: bool = True,
) -> dict:
    """Pick the best non-repetitive ready item, optionally filtered by platform.

    Rotates away from the category of the most-recently-used reserve item so two
    consecutive posts never feel identical. Marks the chosen item used by default.
    """
    repo = repository or get_repository()
    ready = repo.list_war_chest(reserve_status="ready", limit=1000)
    if platform:
        ready = [r for r in ready if not r.get("platform") or r["platform"] == platform]
    if category:
        ready = [r for r in ready if r["category"] == category]
    if not ready:
        return {"error": "war chest is empty (no ready items match)",
                "platform": platform, "category": category}

    now = _now()
    avoid = _last_used_category(repo)
    best = max(ready, key=lambda r: _score(r, now, avoid_category=avoid))
    if mark_used:
        repo.mark_war_chest_used(best["id"])
    return {"item": best, "rotated_from_category": avoid}


def _last_used_category(repo: Repository) -> str | None:
    """The category of the most recently used reserve item (to rotate away from)."""
    used = repo.list_war_chest(reserve_status="used", limit=50)
    best: dict | None = None
    for u in used:
        if not u.get("last_used_at"):
            continue
        if best is None or u["last_used_at"] > best["last_used_at"]:
            best = u
    return best["category"] if best else None
