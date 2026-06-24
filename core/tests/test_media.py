from invisable_os.media import MediaProducer
from invisable_os.media.renderers import ComfyUIRenderer, default_renderers
from invisable_os.models.content import ContentCandidate, Platform, QueueStatus
from invisable_os.services import produce_media
from invisable_os.store import get_repository


def test_producer_renders_every_flywheel_asset():
    candidate = ContentCandidate(brief="Tool theft", platform=Platform.TIKTOK, hook="Not again.")
    results = MediaProducer().produce(candidate)
    assert len(results) >= 5
    assert all(r.ok for r in results)
    kinds = {r.kind for r in results}
    assert {"tiktok", "reel", "quote_graphic"} <= kinds


def test_comfyui_renderer_dry_run_when_unconfigured(monkeypatch):
    monkeypatch.delenv("COMFYUI_BASE_URL", raising=False)
    r = ComfyUIRenderer().render("tiktok", "a clip", out_dir="data/x")
    assert r.ok
    assert r.backend == "dry-run"


def test_renderers_cover_all_asset_kinds():
    renderers = default_renderers()
    for kind in ("tiktok", "reel", "quote_graphic", "voiceover", "caption", "story_poll"):
        assert any(rd.handles(kind) for rd in renderers), kind


def test_produce_media_persists_to_library():
    repo = get_repository()
    item_id = repo.enqueue(
        {
            "candidate_id": "c1",
            "candidate": {"brief": "Fatigue", "platform": "instagram", "hook": "Hi"},
            "status": QueueStatus.PENDING_REVIEW.value,
            "platform": "instagram",
        }
    )
    res = produce_media(item_id)
    assert res["produced"] >= 5
    library = repo.list_media(item_id)
    assert len(library) == res["produced"]
