"""Generation-model licence gate — the commercial-use axis of copyright safety."""

from fastapi.testclient import TestClient

from invisable_os.guardrails.model_licensing import (
    MODEL_LICENCES,
    get_licence,
    licence_check,
)
from invisable_os.main import app
from invisable_os.media.safe_area import Surface
from invisable_os.media.video_qc import VideoQualityGate, VideoSpec
from invisable_os.models.content import Platform

client = TestClient(app)


# --- Registry ---------------------------------------------------------------


def test_lookup_by_name_and_alias_is_case_insensitive():
    assert get_licence("FLUX.1 [dev]") is get_licence("flux-dev")
    assert get_licence("YOLOv8") is get_licence("ultralytics")
    assert get_licence("not-a-real-model") is None


def test_known_non_commercial_models_are_marked():
    assert get_licence("flux-dev").commercial is False
    assert get_licence("hunyuanvideo").commercial is False  # UK/EU excluded
    assert get_licence("ultralytics").commercial is False  # AGPL
    assert get_licence("flux-schnell").commercial is True
    assert get_licence("wan2.1").commercial is True


# --- The gate ---------------------------------------------------------------


def test_commercial_check_blocks_non_commercial_models():
    v = licence_check(["flux-schnell", "flux-dev", "hunyuanvideo"])
    assert not v.passed
    assert "FLUX.1 [dev]" in v.blocked
    assert "HunyuanVideo" in v.blocked
    assert "FLUX.1 [schnell]" in v.cleared


def test_gate_is_fail_closed_on_unknown_models():
    v = licence_check(["some-brand-new-model"])
    assert not v.passed
    assert "some-brand-new-model" in v.unknown


def test_clean_stack_passes():
    v = licence_check(["flux-schnell", "wan2.1", "kokoro", "whisper"])
    assert v.passed
    assert not v.blocked and not v.unknown


def test_non_commercial_use_allows_registered_models():
    # Internal/reference output: a registered non-commercial model is fine.
    v = licence_check(["flux-dev"], commercial=False)
    assert v.passed
    # But an unregistered model is still flagged even for internal use.
    assert not licence_check(["mystery-model"], commercial=False).passed


# --- Wired into the Video Quality Gate --------------------------------------


def _spec(**kw) -> VideoSpec:
    base = dict(platform=Platform.TIKTOK, surface=Surface.REEL, width=1080, height=1920,
                fps=30.0, duration_s=20.0, sharpness=0.9)
    base.update(kw)
    return VideoSpec(**base)


def _status(report, name):
    return next(c.status for c in report.checks if c.name == name)


def test_video_gate_blocks_non_commercial_generation_model():
    report = VideoQualityGate().check(_spec(generation_models=["flux-dev"]))
    assert _status(report, "model_licence").value == "fail"
    assert not report.passed


def test_video_gate_passes_commercial_safe_model():
    report = VideoQualityGate().check(_spec(generation_models=["flux-schnell"]))
    assert _status(report, "model_licence").value == "pass"


def test_video_gate_no_models_declared_passes():
    report = VideoQualityGate().check(_spec())
    assert _status(report, "model_licence").value == "pass"


# --- API --------------------------------------------------------------------


def test_licensing_models_endpoint():
    data = client.get("/v1/licensing/models").json()
    assert data["count"] == len(MODEL_LICENCES)
    assert any(m["name"] == "FLUX.1 [dev]" and m["commercial"] is False
               for m in data["models"])


def test_licensing_check_endpoint():
    data = client.post(
        "/v1/licensing/check", json={"models": ["flux-dev", "wan2.1"], "commercial": True}
    ).json()
    assert data["passed"] is False
    assert "FLUX.1 [dev]" in data["blocked"]
    assert "Wan 2.1" in data["cleared"]
