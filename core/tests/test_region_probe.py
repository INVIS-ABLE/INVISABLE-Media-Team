"""Region-detector probes: pure geometry + injected-detector path + dry-run."""

import pytest

from invisable_os.media.region_probe import (
    DEFAULT_OBJECT_LABELS,
    ObjectRegionProbe,
    OCRTextProbe,
    OpenCVFaceProbe,
    labelled_detections_to_regions,
    merge_regions,
    pixels_to_box,
)
from invisable_os.media.safe_area import RegionKind
from invisable_os.media.video_qc import (
    BoxModel,
    RegionModel,
    VideoQualityGate,
    VideoSpec,
)
from invisable_os.models.content import Platform

# --- Pure geometry ----------------------------------------------------------


def test_pixels_to_box_normalises_and_clamps():
    box = pixels_to_box(108, 192, 540, 540, 1080, 1920)
    assert (box.x0, box.y0) == (0.1, 0.1)
    assert box.x1 == 0.6
    # A box running past the frame edge is clamped to 1.0.
    edge = pixels_to_box(1000, 1800, 500, 500, 1080, 1920)
    assert edge.x1 == 1.0 and edge.y1 == 1.0


def test_pixels_to_box_rejects_bad_frame():
    with pytest.raises(ValueError):
        pixels_to_box(0, 0, 10, 10, 0, 1920)


def test_merge_regions_unions_same_kind_overlaps():
    a = RegionModel(kind=RegionKind.FACE, box=BoxModel(x0=0.30, y0=0.20, x1=0.60, y1=0.50))
    b = RegionModel(kind=RegionKind.FACE, box=BoxModel(x0=0.31, y0=0.21, x1=0.61, y1=0.51))
    merged = merge_regions([a, b])
    assert len(merged) == 1
    assert merged[0].box.x0 == 0.30 and merged[0].box.x1 == 0.61  # union


def test_merge_regions_keeps_different_kinds_separate():
    face = RegionModel(kind=RegionKind.FACE, box=BoxModel(x0=0.3, y0=0.2, x1=0.6, y1=0.5))
    text = RegionModel(kind=RegionKind.ON_SCREEN_TEXT, box=BoxModel(x0=0.3, y0=0.2, x1=0.6, y1=0.5))
    assert len(merge_regions([face, text])) == 2


def test_merge_regions_keeps_distant_same_kind_separate():
    a = RegionModel(kind=RegionKind.FACE, box=BoxModel(x0=0.0, y0=0.0, x1=0.2, y1=0.2))
    b = RegionModel(kind=RegionKind.FACE, box=BoxModel(x0=0.7, y0=0.7, x1=0.9, y1=0.9))
    assert len(merge_regions([a, b])) == 2


# --- Face probe (injected detector) -----------------------------------------


def test_face_probe_appends_normalised_face_regions():
    # One face in the lower third, present across two sampled frames.
    def detector(path, n):
        return [
            (1080, 1920, [(300, 1100, 400, 400)]),
            (1080, 1920, [(305, 1105, 400, 400)]),
        ]

    probe = OpenCVFaceProbe(detector=detector, force_available=True)
    spec = probe.probe("clip.mp4", VideoSpec())
    assert len(spec.regions) == 1  # the two frames merged into one face
    face = spec.regions[0]
    assert face.kind == RegionKind.FACE
    assert face.box.y0 == pytest.approx(0.5729, abs=0.01)


def test_face_probe_preserves_existing_regions():
    existing = RegionModel(kind=RegionKind.LOGO, box=BoxModel(x0=0.0, y0=0.0, x1=0.1, y1=0.1))
    probe = OpenCVFaceProbe(
        detector=lambda p, n: [(1080, 1920, [(300, 300, 200, 200)])], force_available=True
    )
    spec = probe.probe("clip.mp4", VideoSpec(regions=[existing]))
    kinds = {r.kind for r in spec.regions}
    assert RegionKind.LOGO in kinds and RegionKind.FACE in kinds


def test_face_probe_dry_run_when_opencv_absent():
    probe = OpenCVFaceProbe()
    if probe.available:  # pragma: no cover - only where cv2 is installed
        return
    spec = probe.probe("clip.mp4", VideoSpec())
    assert spec.regions == []


def test_face_probe_survives_detector_error():
    def boom(path, n):
        raise RuntimeError("cascade missing")

    probe = OpenCVFaceProbe(detector=boom, force_available=True)
    spec = probe.probe("clip.mp4", VideoSpec())
    assert spec.regions == []  # error swallowed, no crash


# --- OCR probe --------------------------------------------------------------


def test_ocr_probe_filters_tiny_specks():
    # One real caption-sized box and one sub-threshold speck.
    def detector(path, n):
        return [(1080, 1920, [(100, 1600, 880, 120), (10, 10, 4, 4)])]

    probe = OCRTextProbe(detector=detector, force_available=True)
    spec = probe.probe("clip.mp4", VideoSpec())
    assert len(spec.regions) == 1
    assert spec.regions[0].kind == RegionKind.ON_SCREEN_TEXT


# --- Feeding the gate end-to-end --------------------------------------------


def test_detected_face_drives_visual_obstruction_check():
    # A caption placed over where the detector finds a face must fail the gate.
    def face_detector(path, n):
        return [(1080, 1920, [(324, 384, 432, 576)])]  # face ~y 0.2–0.5

    spec = OpenCVFaceProbe(detector=face_detector, force_available=True).probe(
        "clip.mp4",
        VideoSpec(
            platform=Platform.TIKTOK,
            width=1080, height=1920, sharpness=0.9,
            caption_boxes=[BoxModel(x0=0.12, y0=0.30, x1=0.77, y1=0.45)],  # over the face
        ),
    )
    report = VideoQualityGate().check(spec)
    obstruction = next(c for c in report.checks if c.name == "visual_obstruction")
    assert obstruction.status.value == "fail"


def test_default_probes_include_region_detectors():
    from invisable_os.media.probes import default_probes

    names = {p.name for p in default_probes()}
    assert {"ffmpeg", "whisper", "opencv-face", "ocr-text", "object-region"} <= names


# --- Object probe (AGPL-safe label mapping) ---------------------------------


def test_labelled_detections_map_and_filter():
    frames = [(1080, 1920, [
        ("drill", 300, 300, 200, 200, 0.9),    # tool → HAND_TOOL_PRODUCT
        ("logo", 800, 100, 150, 150, 0.8),     # brand → LOGO
        ("cat", 10, 10, 50, 50, 0.95),         # unknown label → dropped
        ("knife", 400, 1000, 100, 100, 0.2),   # below confidence → dropped
    ])]
    regions = labelled_detections_to_regions(frames, DEFAULT_OBJECT_LABELS)
    kinds = sorted(r.kind.value for r in regions)
    assert kinds == ["hand_tool_product", "logo"]


def test_object_probe_appends_regions_via_injected_detector():
    def detector(path, n):
        return [(1080, 1920, [("hammer", 300, 1100, 200, 200, 0.95)])]

    probe = ObjectRegionProbe(detector=detector)
    spec = probe.probe("clip.mp4", VideoSpec())
    assert len(spec.regions) == 1
    assert spec.regions[0].kind == RegionKind.HAND_TOOL_PRODUCT


def test_object_probe_dry_run_without_detector_or_model(monkeypatch):
    monkeypatch.delenv("OBJECT_DETECT_MODEL", raising=False)
    probe = ObjectRegionProbe()
    assert probe.available is False
    spec = probe.probe("clip.mp4", VideoSpec())
    assert spec.regions == []


def test_object_probe_uses_BSD_opencv_not_agpl_yolo():
    # Guardrail: the licence-clean default backend is OpenCV DNN, and we never
    # import the AGPL Ultralytics package (mentioning it in prose is fine).
    import invisable_os.media.region_probe as rp

    text = open(rp.__file__).read()
    assert "import ultralytics" not in text
    assert "from ultralytics" not in text
    assert "cv2.dnn" in text


def test_object_detected_over_caption_fails_obstruction():
    def detector(path, n):
        return [(1080, 1920, [("drill", 130, 1280, 700, 250, 0.9)])]  # tool ~y0.66–0.79

    spec = ObjectRegionProbe(detector=detector).probe(
        "clip.mp4",
        VideoSpec(
            platform=Platform.TIKTOK, width=1080, height=1920, sharpness=0.9,
            caption_boxes=[BoxModel(x0=0.12, y0=0.66, x1=0.77, y1=0.78)],  # over the tool
        ),
    )
    report = VideoQualityGate().check(spec)
    obstruction = next(c for c in report.checks if c.name == "visual_obstruction")
    assert obstruction.status.value == "fail"
