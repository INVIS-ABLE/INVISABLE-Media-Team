"""Attribution service — which published posts actually drove founder recognition.

The Watchtower learns at the *theme* level and charts the Founder Recognition Index
over time, but until now nothing showed *which individual posts* earned it. This
seam reads every recorded performance signal, splits the index across the posts that
produced it (see :meth:`AlgorithmWatchtower.attribute_recognition`), and joins each
post's display text so the dashboard can show a ranked "top performing posts" list
with a per-metric breakdown. Offline / with no signals it returns an empty list.
"""

from __future__ import annotations

from invisable_os.engines import AlgorithmWatchtower
from invisable_os.store import Repository, get_repository


def post_attribution(
    *,
    limit: int = 10,
    repository: Repository | None = None,
    watchtower: AlgorithmWatchtower | None = None,
) -> dict:
    """Rank published posts by their contribution to the Founder Recognition Index."""
    repo = repository or get_repository()
    signals = repo.list_signals()
    ranked = (watchtower or AlgorithmWatchtower()).attribute_recognition(signals)

    # Join display text (hook / platform / status) from the queue, keyed by
    # candidate_id — the same id the signals carry.
    display: dict[str, dict] = {}
    for item in repo.list_queue(limit=500):
        cid = item.get("candidate_id")
        if not cid or cid in display:
            continue
        candidate = item.get("candidate") or {}
        display[cid] = {
            "hook": candidate.get("hook", ""),
            "platform": item.get("platform") or candidate.get("platform", ""),
            "status": item.get("status"),
        }

    posts = []
    for p in ranked[:limit]:
        meta = display.get(p["candidate_id"], {})
        posts.append({**p, "hook": meta.get("hook", ""),
                      "platform": meta.get("platform", ""), "status": meta.get("status")})

    index = round(sum(p["contribution"] for p in ranked), 4)
    return {"index": index, "attributed_posts": len(ranked), "posts": posts}
