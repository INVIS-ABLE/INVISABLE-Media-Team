"""Media service — produce a queue item's assets and assemble a finished cutdown."""

from __future__ import annotations

import os

from invisable_os.media import MediaProducer, VideoAssembler
from invisable_os.media.assembly import AUDIO_EXTS, VIDEO_EXTS
from invisable_os.models.content import ContentCandidate
from invisable_os.store import Repository, get_repository

# Visuals to prefer when assembling, best first (a real clip beats a still).
_VISUAL_KINDS = ("tiktok", "reel", "quote_graphic", "carousel", "image")


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


def _real_files(assets: list[dict]) -> list[dict]:
    """Library assets that point at an actual file on disk (not dry-run plans)."""
    return [
        a for a in assets
        if a.get("backend") != "dry-run" and os.path.isfile(a.get("path", ""))
    ]


def _pick_visual(real: list[dict]) -> str | None:
    by_kind = {a["kind"]: a["path"] for a in real}
    for kind in _VISUAL_KINDS:
        if kind in by_kind:
            return by_kind[kind]
    # Fall back to any image/video file present.
    for a in real:
        if a["path"].lower().endswith(VIDEO_EXTS) or a["path"].lower().endswith((".png", ".jpg")):
            return a["path"]
    return None


def assemble_post(
    item_id: str,
    *,
    repository: Repository | None = None,
    assembler: VideoAssembler | None = None,
) -> dict:
    """Stitch a post's rendered visual + voiceover + captions into a final cutdown."""
    repo = repository or get_repository()
    if repo.get_queue_item(item_id) is None:
        return {"error": "not found", "id": item_id}

    real = _real_files(repo.list_media(item_id))
    visual = _pick_visual(real)
    audio = next((a["path"] for a in real if a["path"].lower().endswith(AUDIO_EXTS)), None)
    captions = next((a["path"] for a in real if a["path"].lower().endswith(".srt")), None)

    base = os.path.dirname(visual) if visual else f"data/assets/generated/{item_id}"
    out_path = f"{os.path.dirname(base.rstrip('/'))}/final/{item_id}.mp4" if visual else \
        f"{base}/final/{item_id}.mp4"

    result = (assembler or VideoAssembler()).assemble(
        visual=visual, audio=audio, captions=captions, out_path=out_path
    )
    asset_id = repo.add_media_asset(
        queue_item_id=item_id, kind="final_video", spec=result.detail,
        path=result.path, backend=result.backend,
        status="rendered" if result.backend == "ffmpeg" else "planned",
    )
    return {
        "item_id": item_id,
        "backend": result.backend,
        "final_video": result.path,
        "asset_id": asset_id,
        "inputs": {"visual": visual, "audio": audio, "captions": captions},
    }
