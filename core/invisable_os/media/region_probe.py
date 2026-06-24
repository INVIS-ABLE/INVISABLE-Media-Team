"""Region-detector probes for the Video Quality Gate.

These build the protected :class:`~invisable_os.media.video_qc.RegionModel` boxes —
faces and on-screen text — that the gate's ``visual_obstruction`` check and the Visual
Layout Agent depend on. They complete the visual side of the probe seam, after
:mod:`invisable_os.media.probes` covered audio/captions/container.

**Licence note.** Face detection uses OpenCV's **BSD-licensed** Haar cascade (bundled
with ``opencv-python``), *not* Ultralytics YOLO — which is AGPL and flagged by the
model-licence gate. OCR uses Tesseract (Apache-2.0). Both are commercial-clean.

Same idiom as the FFmpeg/Whisper probes: the heavy detector is an **injectable
callable** and ``force_available`` bypasses the import check, so the pure geometry
(pixels → normalised boxes, cross-frame merging) is unit-tested without OpenCV/OCR
installed; the probe degrades to a no-op dry-run when they're absent.
"""

from __future__ import annotations

import logging

from invisable_os.media.safe_area import RegionKind
from invisable_os.media.video_qc import BoxModel, RegionModel, VideoProbe, VideoSpec

log = logging.getLogger(__name__)

# A detection on one sampled frame: frame pixel size + boxes in (x, y, w, h) pixels.
FrameDetections = tuple[int, int, list[tuple[int, int, int, int]]]

DEFAULT_SAMPLE_COUNT = 5
MERGE_IOU = 0.3  # boxes of the same kind overlapping more than this are unioned


def importlib_available(module: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module) is not None


# --- Pure geometry (unit-tested without OpenCV/OCR) -------------------------


def pixels_to_box(x: int, y: int, w: int, h: int, frame_w: int, frame_h: int) -> BoxModel:
    """Convert a pixel bounding box to a normalised ``[0,1]`` :class:`BoxModel`."""
    if frame_w <= 0 or frame_h <= 0:
        raise ValueError("frame dimensions must be positive")
    x0 = max(0.0, min(1.0, x / frame_w))
    y0 = max(0.0, min(1.0, y / frame_h))
    x1 = max(0.0, min(1.0, (x + w) / frame_w))
    y1 = max(0.0, min(1.0, (y + h) / frame_h))
    return BoxModel(x0=round(x0, 4), y0=round(y0, 4), x1=round(x1, 4), y1=round(y1, 4))


def _iou(a: BoxModel, b: BoxModel) -> float:
    ba, bb = a.to_box(), b.to_box()
    inter = ba.intersection(bb)
    if inter is None:
        return 0.0
    union = ba.area + bb.area - inter.area
    return inter.area / union if union > 0 else 0.0


def _union(a: BoxModel, b: BoxModel) -> BoxModel:
    return BoxModel(
        x0=min(a.x0, b.x0), y0=min(a.y0, b.y0),
        x1=max(a.x1, b.x1), y1=max(a.y1, b.y1),
    )


def merge_regions(regions: list[RegionModel], iou: float = MERGE_IOU) -> list[RegionModel]:
    """Union same-kind regions that overlap (e.g. one face across sampled frames)."""
    merged: list[RegionModel] = []
    for region in regions:
        for i, kept in enumerate(merged):
            if kept.kind == region.kind and _iou(kept.box, region.box) >= iou:
                merged[i] = RegionModel(
                    kind=kept.kind,
                    box=_union(kept.box, region.box),
                    confidence=max(kept.confidence, region.confidence),
                    label=kept.label or region.label,
                )
                break
        else:
            merged.append(region)
    return merged


def _detections_to_regions(
    frames: list[FrameDetections], kind: RegionKind, *, label: str = "", min_area: float = 0.0
) -> list[RegionModel]:
    """Flatten per-frame pixel detections into merged, normalised regions."""
    regions: list[RegionModel] = []
    for frame_w, frame_h, boxes in frames:
        for (x, y, w, h) in boxes:
            box = pixels_to_box(x, y, w, h, frame_w, frame_h)
            if box.to_box().area >= min_area:
                regions.append(RegionModel(kind=kind, box=box, label=label))
    return merge_regions(regions)


# --- Face probe (OpenCV Haar cascade — BSD, commercial-clean) ---------------


def _cv2_face_detector(path: str, sample_count: int) -> list[FrameDetections]:  # pragma: no cover
    """Sample frames and run OpenCV's bundled frontal-face Haar cascade."""
    import cv2  # type: ignore

    cap = cv2.VideoCapture(path)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    idxs = (
        [int(total * i / (sample_count + 1)) for i in range(1, sample_count + 1)]
        if total else [0]
    )
    frames: list[FrameDetections] = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        frames.append((w, h, [tuple(int(v) for v in f) for f in faces]))
    cap.release()
    return frames


class OpenCVFaceProbe:
    """Detect faces → ``RegionKind.FACE`` regions (OpenCV Haar cascade, dry-run safe)."""

    name = "opencv-face"

    def __init__(
        self,
        detector=None,
        *,
        force_available: bool = False,
        sample_count: int = DEFAULT_SAMPLE_COUNT,
    ) -> None:
        self._detector = detector or _cv2_face_detector
        self._force = force_available
        self.sample_count = sample_count

    @property
    def available(self) -> bool:
        return self._force or importlib_available("cv2")

    def probe(self, path: str, spec: VideoSpec) -> VideoSpec:
        if not self.available:
            log.info("opencv not installed; OpenCVFaceProbe dry-run for %s", path)
            return spec
        try:
            frames = self._detector(path, self.sample_count)
        except Exception as exc:  # noqa: BLE001 — detection must never crash the pipeline
            log.warning("face detection failed for %s: %s", path, exc)
            return spec
        faces = _detections_to_regions(frames, RegionKind.FACE, label="detected")
        return spec.model_copy(update={"regions": [*spec.regions, *faces]})


# --- OCR text probe (Tesseract — Apache-2.0) --------------------------------


class OCRTextProbe:
    """Detect on-screen text → ``RegionKind.ON_SCREEN_TEXT`` regions (dry-run safe)."""

    name = "ocr-text"

    def __init__(
        self,
        detector=None,
        *,
        force_available: bool = False,
        sample_count: int = DEFAULT_SAMPLE_COUNT,
    ) -> None:
        self._detector = detector  # default wired lazily to avoid importing pytesseract
        self._force = force_available
        self.sample_count = sample_count

    @property
    def available(self) -> bool:
        return self._force or (
            importlib_available("pytesseract") and importlib_available("cv2")
        )

    def probe(self, path: str, spec: VideoSpec) -> VideoSpec:
        if not self.available:
            log.info("tesseract/opencv not installed; OCRTextProbe dry-run for %s", path)
            return spec
        detector = self._detector or _tesseract_text_detector
        try:
            frames = detector(path, self.sample_count)
        except Exception as exc:  # noqa: BLE001
            log.warning("OCR failed for %s: %s", path, exc)
            return spec
        # Small specks are usually noise; keep boxes covering at least 0.2% of frame.
        text = _detections_to_regions(
            frames, RegionKind.ON_SCREEN_TEXT, label="ocr", min_area=0.002
        )
        return spec.model_copy(update={"regions": [*spec.regions, *text]})


def _tesseract_text_detector(  # pragma: no cover
    path: str, sample_count: int
) -> list[FrameDetections]:
    import cv2  # type: ignore
    import pytesseract  # type: ignore

    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    idxs = (
        [int(total * i / (sample_count + 1)) for i in range(1, sample_count + 1)]
        if total else [0]
    )
    frames: list[FrameDetections] = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        h, w = frame.shape[:2]
        data = pytesseract.image_to_data(frame, output_type=pytesseract.Output.DICT)
        boxes = [
            (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
            for i in range(len(data["text"]))
            if data["text"][i].strip() and int(data.get("conf", ["-1"])[i] or -1) >= 40
        ]
        frames.append((w, h, boxes))
    cap.release()
    return frames


def region_probes() -> list[VideoProbe]:
    """The visual region probes (faces + on-screen text + objects)."""
    return [OpenCVFaceProbe(), OCRTextProbe(), ObjectRegionProbe()]


# --- Object probe (AGPL-safe: OpenCV DNN + a permissively-licensed model) ----

# A detection on one frame, with a class label and confidence per box.
LabelledFrame = tuple[int, int, list[tuple[str, int, int, int, int, float]]]

# Map detector class labels (lower-case) → the protected region kind they imply.
# Conservative defaults aimed at trades/founder content; extend per the model used.
DEFAULT_OBJECT_LABELS: dict[str, RegionKind] = {
    # tools & products in shot — must not be covered by a caption
    "knife": RegionKind.HAND_TOOL_PRODUCT,
    "scissors": RegionKind.HAND_TOOL_PRODUCT,
    "hammer": RegionKind.HAND_TOOL_PRODUCT,
    "drill": RegionKind.HAND_TOOL_PRODUCT,
    "wrench": RegionKind.HAND_TOOL_PRODUCT,
    "screwdriver": RegionKind.HAND_TOOL_PRODUCT,
    "saw": RegionKind.HAND_TOOL_PRODUCT,
    "tool": RegionKind.HAND_TOOL_PRODUCT,
    "bottle": RegionKind.HAND_TOOL_PRODUCT,
    "cup": RegionKind.HAND_TOOL_PRODUCT,
    "laptop": RegionKind.HAND_TOOL_PRODUCT,
    "cell phone": RegionKind.HAND_TOOL_PRODUCT,
    "book": RegionKind.HAND_TOOL_PRODUCT,
    # brand marks
    "logo": RegionKind.LOGO,
    "watermark": RegionKind.LOGO,
    "brand": RegionKind.LOGO,
    "sponsor": RegionKind.SPONSOR_PRODUCT,
}

MIN_OBJECT_CONFIDENCE = 0.4


def labelled_detections_to_regions(
    frames: list[LabelledFrame],
    label_map: dict[str, RegionKind],
    *,
    min_confidence: float = MIN_OBJECT_CONFIDENCE,
) -> list[RegionModel]:
    """Map labelled pixel detections → merged, normalised protected regions.

    Labels not in ``label_map`` are ignored (we only protect what matters), and
    detections below ``min_confidence`` are dropped.
    """
    regions: list[RegionModel] = []
    for frame_w, frame_h, boxes in frames:
        for (label, x, y, w, h, conf) in boxes:
            kind = label_map.get(label.lower())
            if kind is None or conf < min_confidence:
                continue
            regions.append(
                RegionModel(kind=kind, box=pixels_to_box(x, y, w, h, frame_w, frame_h),
                            confidence=round(conf, 3), label=label)
            )
    return merge_regions(regions)


class ObjectRegionProbe:
    """Detect tools/products/logos → protected regions (OpenCV DNN, dry-run safe).

    The default real backend is OpenCV's DNN module (BSD) loading a
    **permissively-licensed** model configured via ``OBJECT_DETECT_MODEL`` /
    ``OBJECT_DETECT_CONFIG`` — deliberately *not* Ultralytics YOLO (AGPL, blocked by
    the model-licence gate). Without a model configured it degrades to a no-op
    dry-run; the label→region mapping is pure and unit-tested via an injected detector.
    """

    name = "object-region"

    def __init__(
        self,
        detector=None,
        *,
        force_available: bool = False,
        label_map: dict[str, RegionKind] | None = None,
        min_confidence: float = MIN_OBJECT_CONFIDENCE,
        sample_count: int = DEFAULT_SAMPLE_COUNT,
    ) -> None:
        self._detector = detector
        self._force = force_available
        self.label_map = label_map or DEFAULT_OBJECT_LABELS
        self.min_confidence = min_confidence
        self.sample_count = sample_count

    @property
    def available(self) -> bool:
        if self._force or self._detector is not None:
            return True
        import os

        return importlib_available("cv2") and bool(os.getenv("OBJECT_DETECT_MODEL"))

    def probe(self, path: str, spec: VideoSpec) -> VideoSpec:
        if not self.available:
            log.info("object detector not configured; ObjectRegionProbe dry-run for %s", path)
            return spec
        detector = self._detector or _cv2_dnn_object_detector
        try:
            frames = detector(path, self.sample_count)
        except Exception as exc:  # noqa: BLE001
            log.warning("object detection failed for %s: %s", path, exc)
            return spec
        objects = labelled_detections_to_regions(
            frames, self.label_map, min_confidence=self.min_confidence
        )
        return spec.model_copy(update={"regions": [*spec.regions, *objects]})


def _cv2_dnn_object_detector(  # pragma: no cover
    path: str, sample_count: int
) -> list[LabelledFrame]:
    """OpenCV DNN inference with a permissively-licensed model (paths via env)."""
    import os

    import cv2  # type: ignore

    model = os.environ["OBJECT_DETECT_MODEL"]
    config = os.getenv("OBJECT_DETECT_CONFIG", "")
    labels_path = os.getenv("OBJECT_DETECT_LABELS", "")
    labels = (
        [ln.strip() for ln in open(labels_path) if ln.strip()] if labels_path else []
    )
    net = cv2.dnn.readNet(model, config) if config else cv2.dnn.readNet(model)

    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    idxs = (
        [int(total * i / (sample_count + 1)) for i in range(1, sample_count + 1)]
        if total else [0]
    )
    frames: list[LabelledFrame] = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, size=(300, 300), swapRB=True)
        net.setInput(blob)
        detections = net.forward()
        boxes: list[tuple[str, int, int, int, int, float]] = []
        for det in detections[0, 0]:
            conf = float(det[2])
            class_id = int(det[1])
            label = labels[class_id] if 0 <= class_id < len(labels) else str(class_id)
            x0, y0, x1, y1 = (det[3] * w, det[4] * h, det[5] * w, det[6] * h)
            boxes.append((label, int(x0), int(y0), int(x1 - x0), int(y1 - y0), conf))
        frames.append((w, h, boxes))
    cap.release()
    return frames
