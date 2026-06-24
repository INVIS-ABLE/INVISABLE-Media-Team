"""The Video Quality Gate — the full pre-approval checklist."""

from invisable_os.media.safe_area import RegionKind, Surface
from invisable_os.media.video_qc import (
    AudioStats,
    BoxModel,
    CaptionCue,
    CheckStatus,
    RegionModel,
    VideoQualityGate,
    VideoSpec,
)
from invisable_os.models.content import Platform


def _clean_spec(**overrides) -> VideoSpec:
    base = dict(
        platform=Platform.TIKTOK,
        surface=Surface.REEL,
        width=1080,
        height=1920,
        fps=30.0,
        duration_s=22.0,
        audio=AudioStats(
            integrated_lufs=-14.0, true_peak_db=-1.5, voice_present=True,
            music_present=True, voice_over_music_db=10.0, music_licensed=True,
        ),
        captions=[
            CaptionCue(start=0.5, end=2.5, text="You don't look ill"),
            CaptionCue(start=2.6, end=4.6, text="but it's real"),
        ],
        caption_boxes=[BoxModel(x0=0.12, y0=0.66, x1=0.77, y1=0.78)],
        regions=[
            RegionModel(kind=RegionKind.FOUNDER_FACE,
                        box=BoxModel(x0=0.3, y0=0.2, x1=0.7, y1=0.5), label="stephen"),
        ],
        transcript="you don't look ill but it's real",
        sharpness=0.9,
        clutter=0.2,
    )
    base.update(overrides)
    return VideoSpec(**base)


def test_clean_clip_passes_the_gate():
    report = VideoQualityGate().check(_clean_spec())
    assert report.passed, report.failures
    assert not report.warnings


def _status(report, name) -> CheckStatus:
    return next(c.status for c in report.checks if c.name == name)


def test_wrong_aspect_ratio_fails():
    report = VideoQualityGate().check(_clean_spec(width=1080, height=1080))
    assert _status(report, "aspect_ratio") == CheckStatus.FAIL
    assert not report.passed


def test_low_resolution_fails():
    report = VideoQualityGate().check(_clean_spec(width=540, height=960))
    assert _status(report, "resolution") == CheckStatus.FAIL


def test_audio_clipping_fails():
    report = VideoQualityGate().check(
        _clean_spec(audio=AudioStats(true_peak_db=0.5))
    )
    assert _status(report, "audio_clipping") == CheckStatus.FAIL


def test_overlapping_narration_fails():
    report = VideoQualityGate().check(
        _clean_spec(audio=AudioStats(overlapping_narration=True))
    )
    assert _status(report, "overlapping_narration") == CheckStatus.FAIL


def test_unlicensed_music_fails():
    audio = AudioStats(music_present=True, music_licensed=False, voice_over_music_db=10)
    report = VideoQualityGate().check(_clean_spec(audio=audio))
    assert _status(report, "music_licence") == CheckStatus.FAIL


def test_voice_buried_under_music_fails():
    audio = AudioStats(music_present=True, voice_over_music_db=2.0, music_licensed=True)
    report = VideoQualityGate().check(_clean_spec(audio=audio))
    assert _status(report, "voice_music_balance") == CheckStatus.FAIL


def test_caption_over_face_fails_visual_obstruction():
    # Caption band over the founder's face (which sits at y 0.2–0.5).
    report = VideoQualityGate().check(
        _clean_spec(caption_boxes=[BoxModel(x0=0.12, y0=0.30, x1=0.77, y1=0.45)])
    )
    assert _status(report, "visual_obstruction") == CheckStatus.FAIL


def test_caption_under_platform_ui_fails():
    report = VideoQualityGate().check(
        _clean_spec(caption_boxes=[BoxModel(x0=0.1, y0=0.85, x1=0.7, y1=0.95)])
    )
    assert _status(report, "platform_ui_clear") == CheckStatus.FAIL
    assert _status(report, "edge_safe") == CheckStatus.FAIL


def test_duplicate_and_mistimed_captions_fail():
    report = VideoQualityGate().check(
        _clean_spec(captions=[
            CaptionCue(start=0.5, end=2.5, text="same line"),
            CaptionCue(start=2.5, end=12.5, text="same line"),  # duplicate + too long
        ])
    )
    assert _status(report, "caption_duplication") == CheckStatus.FAIL
    assert _status(report, "caption_timing") == CheckStatus.FAIL


def test_broken_subtitles_fail():
    report = VideoQualityGate().check(
        _clean_spec(captions=[CaptionCue(start=3.0, end=2.0, text="reversed")])
    )
    assert _status(report, "subtitles_valid") == CheckStatus.FAIL


def test_caption_accuracy_against_transcript():
    report = VideoQualityGate().check(
        _clean_spec(transcript="completely different words that were actually spoken aloud")
    )
    assert _status(report, "caption_accuracy") == CheckStatus.FAIL


def test_blurry_output_fails():
    report = VideoQualityGate().check(_clean_spec(sharpness=0.1))
    assert _status(report, "sharpness") == CheckStatus.FAIL


def test_report_summary_shape():
    summary = VideoQualityGate().check(_clean_spec(width=1080, height=1080)).summary()
    assert summary["passed"] is False
    assert "aspect_ratio" in summary["failures"]
    assert isinstance(summary["checks"], list)
