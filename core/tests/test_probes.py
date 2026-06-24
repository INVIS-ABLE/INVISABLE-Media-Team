"""Real FFmpeg/Whisper probes: pure parsers + injectable-runner real path + dry-run."""

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.media.probes import (
    FFmpegProbe,
    WhisperProbe,
    parse_ebur128,
    parse_ffprobe,
    probe_video,
)
from invisable_os.media.video_qc import VideoQualityGate, VideoSpec

client = TestClient(app)

# Captured tool output — what ffprobe / ffmpeg actually emit.
SAMPLE_FFPROBE = """
{
  "streams": [
    {"codec_type": "video", "width": 1080, "height": 1920,
     "avg_frame_rate": "30000/1001", "duration": "21.5"},
    {"codec_type": "audio", "channels": 2}
  ],
  "format": {"duration": "21.521"}
}
"""

SAMPLE_EBUR128 = """
[Parsed_ebur128_0 @ 0x55] Summary:

  Integrated loudness:
    I:         -14.2 LUFS
    Threshold: -24.7 LUFS

  True peak:
    Peak:       -1.3 dBFS
"""


# --- Pure parsers -----------------------------------------------------------


def test_parse_ffprobe_extracts_container_metadata():
    meta = parse_ffprobe(SAMPLE_FFPROBE)
    assert meta["width"] == 1080
    assert meta["height"] == 1920
    assert meta["fps"] == 29.97  # 30000/1001
    assert meta["duration_s"] == 21.521
    assert meta["has_audio"] is True


def test_parse_ffprobe_no_audio_stream():
    j = '{"streams": [{"codec_type": "video", "width": 1080, "height": 1920, ' \
        '"avg_frame_rate": "25/1"}], "format": {"duration": "10"}}'
    meta = parse_ffprobe(j)
    assert meta["has_audio"] is False
    assert meta["fps"] == 25.0


def test_parse_ebur128_extracts_loudness_and_peak():
    stats = parse_ebur128(SAMPLE_EBUR128)
    assert stats["integrated_lufs"] == -14.2
    assert stats["true_peak_db"] == -1.3


# --- FFmpeg probe: real path via injected runners ---------------------------


def test_ffmpeg_probe_enriches_spec_from_tool_output():
    probe = FFmpegProbe(
        ffprobe_runner=lambda path: SAMPLE_FFPROBE,
        ebur128_runner=lambda path: SAMPLE_EBUR128,
        force_available=True,
    )
    spec = probe.probe("clip.mp4", VideoSpec(width=0, height=0, fps=0.0, duration_s=0.0))
    assert spec.probe_backend == "ffmpeg"
    assert spec.width == 1080 and spec.height == 1920
    assert spec.fps == 29.97
    assert spec.duration_s == 21.521
    assert spec.audio.integrated_lufs == -14.2
    assert spec.audio.true_peak_db == -1.3


def test_ffmpeg_probe_falls_back_to_dry_run_on_tool_error():
    def boom(path):
        raise OSError("ffprobe exploded")

    probe = FFmpegProbe(ffprobe_runner=boom, force_available=True)
    spec = probe.probe("clip.mp4", VideoSpec())
    assert spec.probe_backend == "dry-run"


def test_ffmpeg_probe_dry_run_when_binary_absent():
    # No force_available and ffprobe isn't installed in this environment.
    probe = FFmpegProbe()
    if probe.available:  # pragma: no cover - only on a box with ffmpeg
        return
    spec = probe.probe("clip.mp4", VideoSpec())
    assert spec.probe_backend == "dry-run"


# --- Whisper probe ----------------------------------------------------------


def test_whisper_probe_dry_run_when_lib_absent():
    probe = WhisperProbe()
    if probe.available:  # pragma: no cover - only where faster_whisper is installed
        return
    spec = probe.probe("clip.mp4", VideoSpec(transcript="kept"))
    assert spec.transcript == "kept"  # unchanged passthrough


# --- Orchestration + gate ---------------------------------------------------


def test_probe_video_runs_probes_in_order_and_feeds_the_gate():
    fake_ffmpeg = FFmpegProbe(
        ffprobe_runner=lambda p: SAMPLE_FFPROBE,
        ebur128_runner=lambda p: SAMPLE_EBUR128,
        force_available=True,
    )
    spec = probe_video("clip.mp4", VideoSpec(), probes=[fake_ffmpeg])
    assert spec.width == 1080 and spec.audio.integrated_lufs == -14.2
    # A probed spec flows straight into the gate.
    report = VideoQualityGate().check(spec)
    assert next(c.status.value for c in report.checks if c.name == "aspect_ratio") == "pass"


def test_probe_video_dry_run_passthrough():
    spec = probe_video("/nope.mp4", VideoSpec(width=1080, height=1920))
    assert spec.width == 1080  # unchanged
    assert spec.probe_backend == "dry-run"


# --- API --------------------------------------------------------------------


def test_video_probe_endpoint_dry_run():
    body = {"path": "/not/a/real/file.mp4",
            "spec": {"platform": "tiktok", "surface": "reel",
                     "width": 1080, "height": 1920, "sharpness": 0.9}}
    data = client.post("/v1/video/probe", json=body).json()
    assert data["spec"]["probe_backend"] == "dry-run"
    assert "report" in data and "passed" in data["report"]
