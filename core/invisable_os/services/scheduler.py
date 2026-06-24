"""Scheduler service — take approved/scheduled items live via the publisher.

Approved content is published (dry-run by default), marked PUBLISHED, and a seed
performance signal is recorded so the Watchtower has a row to learn from once real
metrics arrive.
"""

from __future__ import annotations

from invisable_os.models.content import QueueStatus
from invisable_os.publish import Publisher, get_publisher
from invisable_os.store import Repository, get_repository


def publish_due(
    *,
    limit: int = 20,
    repository: Repository | None = None,
    publisher: Publisher | None = None,
) -> dict:
    """Publish approved (and already-scheduled) items. Returns a small report."""
    repo = repository or get_repository()
    pub = publisher or get_publisher()

    due = repo.list_queue(QueueStatus.APPROVED.value, limit=limit)
    due += repo.list_queue(QueueStatus.SCHEDULED.value, limit=limit)

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
