"""Media service — produce a queue item's assets and store them in the library."""

from __future__ import annotations

from invisable_os.media import MediaProducer
from invisable_os.models.content import ContentCandidate
from invisable_os.store import Repository, get_repository


def produce_media(
    item_id: str,
    *,
    repository: Repository | None = None,
    producer: MediaProducer | None = None,
) -> dict:
    """Render the flywheel assets for a queued item and record them in the library."""
    repo = repository or get_repository()
    item = repo.get_queue_item(item_id)
    if item is None:
        return {"error": "not found", "id": item_id}

    candidate = ContentCandidate(**item["candidate"])
    results = (producer or MediaProducer()).produce(candidate)

    stored = []
    for r in results:
        asset_id = repo.add_media_asset(
            queue_item_id=item_id, kind=r.kind, spec=r.detail, path=r.path, backend=r.backend
        )
        stored.append({"id": asset_id, "kind": r.kind, "backend": r.backend, "path": r.path})
    return {"item_id": item_id, "produced": len(stored), "assets": stored}
