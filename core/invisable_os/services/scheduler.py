"""Scheduler service — take approved/scheduled items live via the publisher.

Approved content is published (dry-run by default), marked PUBLISHED, and a seed
performance signal is recorded so the Watchtower has a row to learn from once real
metrics arrive.
"""

from __future__ import annotations

from datetime import UTC, datetime

from invisable_os.models.content import QueueStatus
from invisable_os.publish import Publisher, get_publisher
from invisable_os.publish.postiz import PostizPublisher
from invisable_os.store import Repository, get_repository


def publish_due(
    *,
    limit: int = 20,
    now: datetime | None = None,
    repository: Repository | None = None,
    publisher: Publisher | None = None,
) -> dict:
    """Publish due items: approved (immediate) + scheduled items whose time has come."""
    repo = repository or get_repository()
    pub = publisher or get_publisher()

    due = repo.due_for_publish(now or datetime.now(UTC), limit=limit)

    published, failed = [], []
    for item in due:
        result = pub.publish(item)
        if result.ok:
            repo.transition(item["id"], QueueStatus.PUBLISHED, tags=item.get("tags", []))
            repo.record_signal(item["candidate_id"], item.get("platform", ""), "published", 1.0)
            published.append({"id": item["id"], "external_id": result.external_id})
        else:
            failed.append({"id": item["id"], "detail": result.detail})

    return {"backend": pub.name, "published": published, "failed": failed, "count": len(published)}


def schedule_to_postiz(
    item_id: str,
    when: datetime,
    *,
    repository: Repository | None = None,
    publisher: PostizPublisher | None = None,
) -> dict:
    """Hand an approved item to Postiz to schedule natively at ``when``.

    On success the item is marked SCHEDULED with Postiz's external id; the
    Postiz Scheduler Agent's real action. Falls back to a clear error (never raises)
    when Postiz isn't configured or the call fails, so the operator sees why.
    """
    repo = repository or get_repository()
    item = repo.get_queue_item(item_id)
    if not item:
        return {"ok": False, "error": "not found", "id": item_id}

    pub = publisher or PostizPublisher()
    result = pub.schedule(item, when)
    if result.ok:
        repo.transition(item_id, QueueStatus.SCHEDULED, tags=item.get("tags", []))
    return {
        "ok": result.ok,
        "id": item_id,
        "backend": result.backend,
        "external_id": result.external_id,
        "scheduled_for": when.isoformat(),
        "detail": result.detail,
    }
