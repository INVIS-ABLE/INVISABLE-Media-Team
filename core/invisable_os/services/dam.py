"""DAM sync service — push a post's finished assets into ResourceSpace.

Real, on-disk library assets (produced/assembled media) are uploaded to ResourceSpace
and a ``dam_ref`` is recorded against the post. Degrades to a dry-run plan when
ResourceSpace isn't configured or a file isn't a real local file yet.
"""

from __future__ import annotations

import logging

from invisable_os.integrations import ResourceSpaceClient
from invisable_os.services.media import _real_files
from invisable_os.store import Repository, get_repository

log = logging.getLogger(__name__)


def sync_post_to_dam(
    item_id: str,
    *,
    repository: Repository | None = None,
    client: ResourceSpaceClient | None = None,
) -> dict:
    """Sync a post's real media assets into ResourceSpace; record dam_refs."""
    repo = repository or get_repository()
    if repo.get_queue_item(item_id) is None:
        return {"error": "not found", "id": item_id}

    rs = client or ResourceSpaceClient()
    real = _real_files(repo.list_media(item_id))
    if not real:
        return {"item_id": item_id, "backend": "dry-run", "synced": [],
                "detail": "no real media to sync (run produce/assemble with a backend first)"}

    synced = []
    for asset in real:
        if rs.configured:
            try:
                res = rs.sync_file(asset["path"], title=f"{item_id}:{asset['kind']}")
                ref_id = repo.add_media_asset(
                    item_id, "dam_ref", f"resourcespace {res['ref']}", res["url"], "resourcespace"
                )
                synced.append(
                    {"id": ref_id, "kind": asset["kind"], "ref": res["ref"], "url": res["url"]}
                )
                continue
            except Exception as exc:  # noqa: BLE001 — degrade per asset, never crash
                log.warning("ResourceSpace sync failed for %s: %s", asset["path"], exc)
        # Dry-run fallback for this asset.
        ref_id = repo.add_media_asset(
            item_id, "dam_ref", f"[dry-run] would sync {asset['kind']}", asset["path"], "dry-run"
        )
        synced.append({"id": ref_id, "kind": asset["kind"], "ref": None, "url": asset["path"]})

    backend = "resourcespace" if rs.configured else "dry-run"
    return {"item_id": item_id, "backend": backend, "synced": synced, "count": len(synced)}
