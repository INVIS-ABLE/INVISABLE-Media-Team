"""Export Gate — the composed 7-category export contract over the video quality gate."""

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.media.export_gate import EXPORT_CATEGORIES, export_gate
from invisable_os.media.safe_area import RegionKind
from invisable_os.media.video_qc import (
    AudioStats,
    BoxModel,
    RegionModel,
    VideoQualityGate,
    VideoSpec,
)
from invisable_os.models.content import Platform

client = TestClient(app)


def _rich_spec(**over) -> VideoSpec:
    """A spec that triggers as many granular checks as possible."""
    base = dict(
        platform=Platform.TIKTOK, width=1080, height=1920, fps=30, duration_s=20,
        audio=AudioStats(music_present=True, voice_present=True),
        captions=[{"start": 0.0, "end": 2.0, "text": "hello"},
                  {"start": 2.0, "end": 4.0, "text": "world"}],
        transcript="hello world",
        caption_boxes=[BoxModel(x0=0.1, y0=0.8, x1=0.7, y1=0.88)],
        regions=[RegionModel(kind=RegionKind.FACE,
                             box=BoxModel(x0=0.1, y0=0.2, x1=0.6, y1=0.45))],
        generation_models=["flux-schnell"],
    )
    base.update(over)
    return VideoSpec(**base)


def test_every_gate_check_maps_to_a_category():
    """Guardrail: no gate check can slip past export_ready unmapped."""
    mapped = set().union(*(names for _, _, names in EXPORT_CATEGORIES))
    report = VideoQualityGate().check(_rich_spec())
    emitted = {c.name for c in report.checks}
    assert emitted <= mapped, f"unmapped gate checks: {emitted - mapped}"


def test_clean_clip_is_export_ready():
    out = export_gate(VideoSpec(platform=Platform.TIKTOK, width=1080, height=1920,
                                fps=30, duration_s=20, sharpness=0.9))
    assert out["export_ready"] is True
    assert out["blocking"] == []
    # All seven+ categories are present and none failed.
    assert {c["label"] for c in out["categories"]} >= {
        "Audio clarity", "Caption timing", "Safe zone", "Face & object obstruction",
        "Text overlap", "Platform aspect ratio", "Copyright / risk",
    }


def test_flawed_clip_is_blocked_with_reasons():
    spec = _rich_spec(
        width=1080, height=1080,  # wrong aspect for a reel
        duration_s=1.0,           # too short
        sharpness=0.1,            # blurry
        audio=AudioStats(true_peak_db=1.0, music_present=True, music_licensed=False,
                         voice_present=True, voice_over_music_db=1.0),
        generation_models=["flux-dev"],  # non-commercial licence
        commercial_use=True,
        caption_boxes=[BoxModel(x0=0.12, y0=0.30, x1=0.55, y1=0.42)],  # over the face
    )
    out = export_gate(spec)
    assert out["export_ready"] is False
    labels = set(out["blocking"])
    assert "Platform aspect ratio" in labels   # aspect + duration
    assert "Visual quality" in labels          # sharpness
    assert "Copyright / risk" in labels        # unlicensed music + flux-dev
    assert "Face & object obstruction" in labels  # caption over the face


def test_text_overlap_is_separate_from_face_obstruction():
    # A caption over on-screen TEXT fails text_overlap but not visual_obstruction.
    spec = VideoSpec(
        platform=Platform.TIKTOK, width=1080, height=1920, sharpness=0.9,
        regions=[RegionModel(kind=RegionKind.ON_SCREEN_TEXT,
                             box=BoxModel(x0=0.1, y0=0.3, x1=0.7, y1=0.5))],
        caption_boxes=[BoxModel(x0=0.12, y0=0.32, x1=0.66, y1=0.46)],
    )
    by_label = {c["label"]: c["status"] for c in export_gate(spec)["categories"]}
    assert by_label["Text overlap"] == "fail"
    assert by_label["Face & object obstruction"] == "pass"


def test_export_gate_endpoint():
    r = client.post("/v1/export/gate", json={"platform": "tiktok", "width": 1080,
                                             "height": 1920, "fps": 30, "duration_s": 20,
                                             "sharpness": 0.9})
    assert r.status_code == 200
    body = r.json()
    assert body["export_ready"] is True
    assert "categories" in body
