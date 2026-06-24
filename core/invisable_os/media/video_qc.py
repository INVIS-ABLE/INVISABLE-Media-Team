"""Video Quality Gate.

No video reaches the approval queue until it clears this gate. It runs the full
pre-approval checklist from the build directive — aspect ratio, resolution, audio
loudness/clipping/balance, caption timing/accuracy/duplication, and (via the Visual
Layout Agent) visual obstruction and safe-area compliance.

The gate is **pure logic over a :class:`VideoSpec`** — a structured description of a
rendered clip. The heavy detectors that build that description (FFmpeg for
container/loudness, Whisper for the transcript, OpenCV/YOLO for faces and objects,
OCR for on-screen text) live behind the :class:`VideoProbe` protocol and degrade to
a dry-run when their binaries aren't installed — exactly like the renderers. That
keeps the gate fast, deterministic and fully testable here, while leaving a clean
seam for the GPU box to plug the real probes in.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from invisable_os.guardrails.model_licensing import licence_check
from invisable_os.media.safe_area import (
    Aspect,
    Box,
    Region,
    RegionKind,
    Surface,
    VisualLayoutAgent,
    get_template,
    matches_aspect,
)
from invisable_os.models.content import Platform

# --- Thresholds (centralised so they are easy to tune) ----------------------

TARGET_LUFS = -14.0  # social platforms normalise toward ~-14 LUFS integrated
LUFS_TOLERANCE = 2.0
MAX_TRUE_PEAK_DB = -1.0  # above this is clipping risk
MIN_VOICE_OVER_MUSIC_DB = 6.0  # voice should sit clearly above the bed
MIN_SHORT_SIDE = 1080  # vertical video should be at least 1080 wide
MIN_FPS = 24.0
MIN_DURATION_S = 3.0
MAX_DURATION_S = 180.0
MIN_CUE_S = 0.4  # a caption flashed for less than this is unreadable
MAX_CUE_S = 7.0  # a single cue lingering longer than this is badly timed
MIN_CAPTION_ACCURACY = 0.8  # token coverage of spoken words by the subtitles
MIN_SHARPNESS = 0.4  # 0–1, higher is sharper (normalised blur score)
MAX_CLUTTER = 0.7  # 0–1, higher is busier

# Aspect expected per surface.
_SURFACE_ASPECT = {
    Surface.REEL: "9:16",
    Surface.STORY: "9:16",
}

# Regions that must never be covered by a caption/overlay. Split so the gate can
# report "face/object obstruction" and "text overlap" as the two distinct checks the
# export contract names.
_PROTECTED_TEXT = {
    RegionKind.ON_SCREEN_TEXT,
    RegionKind.IMPORTANT_TEXT,
}
_PROTECTED_VISUAL = {
    RegionKind.FACE,
    RegionKind.FOUNDER_FACE,
    RegionKind.COMMUNITY_FACE,
    RegionKind.HAND_TOOL_PRODUCT,
    RegionKind.LOGO,
    RegionKind.SPONSOR_PRODUCT,
}
_PROTECTED = _PROTECTED_VISUAL | _PROTECTED_TEXT


class CheckStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"  # surfaced but does not block the gate
    FAIL = "fail"  # blocks the gate


# --- Structured inputs -------------------------------------------------------


class AudioStats(BaseModel):
    integrated_lufs: float = TARGET_LUFS
    true_peak_db: float = -3.0
    voice_present: bool = True
    music_present: bool = False
    voice_over_music_db: float = 12.0  # how far voice sits above the music bed
    overlapping_narration: bool = False
    music_licensed: bool = True


class CaptionCue(BaseModel):
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return self.end - self.start


class BoxModel(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    def to_box(self) -> Box:
        return Box(self.x0, self.y0, self.x1, self.y1)


class RegionModel(BaseModel):
    kind: RegionKind
    box: BoxModel
    confidence: float = 1.0
    label: str = ""

    def to_region(self) -> Region:
        return Region(self.kind, self.box.to_box(), self.confidence, self.label)


class VideoSpec(BaseModel):
    """Everything the gate needs to know about a rendered clip."""

    platform: Platform = Platform.TIKTOK
    surface: Surface = Surface.REEL
    width: int = 1080
    height: int = 1920
    fps: float = 30.0
    duration_s: float = 20.0

    audio: AudioStats = Field(default_factory=AudioStats)
    captions: list[CaptionCue] = Field(default_factory=list)
    caption_boxes: list[BoxModel] = Field(default_factory=list)
    overlays: list[BoxModel] = Field(default_factory=list)
    regions: list[RegionModel] = Field(default_factory=list)

    transcript: str = ""  # spoken words, e.g. from Whisper, for caption accuracy
    sharpness: float = 1.0  # 0–1, from a blur detector; 1 = perfectly sharp
    clutter: float = 0.0  # 0–1, visual busyness; 0 = clean
    probe_backend: str = "annotation"  # how the spec was built (annotation/ffmpeg/…)

    # Generation/detector models used to build the clip (ComfyUI/Flux/Wan/…). Gated
    # for commercial-use licence — e.g. FLUX.1 [dev] is non-commercial.
    generation_models: list[str] = Field(default_factory=list)
    commercial_use: bool = True  # is this clip destined for paid/commercial use?


# --- QC report ---------------------------------------------------------------


class QCCheck(BaseModel):
    name: str
    status: CheckStatus
    detail: str = ""

    @property
    def failed(self) -> bool:
        return self.status == CheckStatus.FAIL


class VideoQCReport(BaseModel):
    checks: list[QCCheck] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(c.failed for c in self.checks)

    @property
    def failures(self) -> list[QCCheck]:
        return [c for c in self.checks if c.status == CheckStatus.FAIL]

    @property
    def warnings(self) -> list[QCCheck]:
        return [c for c in self.checks if c.status == CheckStatus.WARN]

    def summary(self) -> dict:
        return {
            "passed": self.passed,
            "failures": [c.name for c in self.failures],
            "warnings": [c.name for c in self.warnings],
            "checks": [c.model_dump() for c in self.checks],
        }


# --- The probe seam ----------------------------------------------------------


@runtime_checkable
class VideoProbe(Protocol):
    """Builds (or enriches) a :class:`VideoSpec` from a media path.

    Real implementations wrap FFmpeg / Whisper / OpenCV / OCR. The gate never calls
    a probe directly — callers probe first, then gate the resulting spec — so the
    gate stays pure and testable.
    """

    name: str

    def probe(self, path: str, spec: VideoSpec) -> VideoSpec: ...


# --- The gate ----------------------------------------------------------------


def _tokens(text: str) -> list[str]:
    return [t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split()]


class VideoQualityGate:
    """Runs the full pre-approval checklist over a :class:`VideoSpec`."""

    def __init__(self, layout: VisualLayoutAgent | None = None) -> None:
        self.layout = layout or VisualLayoutAgent()

    def check(self, spec: VideoSpec) -> VideoQCReport:
        checks: list[QCCheck] = []
        checks.append(self._aspect(spec))
        checks.append(self._resolution(spec))
        checks.append(self._framerate(spec))
        checks.append(self._duration(spec))
        checks.extend(self._audio(spec))
        checks.extend(self._captions(spec))
        checks.append(self._caption_accuracy(spec))
        checks.extend(self._visual(spec))
        checks.append(self._model_licence(spec))
        return VideoQCReport(checks=checks)

    # -- container ----------------------------------------------------------

    def _aspect(self, spec: VideoSpec) -> QCCheck:
        expected = _SURFACE_ASPECT.get(spec.surface)
        if expected is None:
            return QCCheck(name="aspect_ratio", status=CheckStatus.PASS,
                           detail=f"{spec.surface.value}: no fixed aspect")
        ok = matches_aspect(spec.width, spec.height, Aspect(expected))
        return QCCheck(
            name="aspect_ratio",
            status=CheckStatus.PASS if ok else CheckStatus.FAIL,
            detail=f"{spec.width}x{spec.height} expected {expected}",
        )

    def _resolution(self, spec: VideoSpec) -> QCCheck:
        short_side = min(spec.width, spec.height)
        ok = short_side >= MIN_SHORT_SIDE
        return QCCheck(
            name="resolution",
            status=CheckStatus.PASS if ok else CheckStatus.FAIL,
            detail=f"short side {short_side}px (min {MIN_SHORT_SIDE})",
        )

    def _framerate(self, spec: VideoSpec) -> QCCheck:
        ok = spec.fps >= MIN_FPS
        return QCCheck(
            name="framerate",
            status=CheckStatus.PASS if ok else CheckStatus.WARN,
            detail=f"{spec.fps:.0f}fps (min {MIN_FPS:.0f})",
        )

    def _duration(self, spec: VideoSpec) -> QCCheck:
        ok = MIN_DURATION_S <= spec.duration_s <= MAX_DURATION_S
        return QCCheck(
            name="duration",
            status=CheckStatus.PASS if ok else CheckStatus.FAIL,
            detail=f"{spec.duration_s:.1f}s (allowed {MIN_DURATION_S:.0f}–{MAX_DURATION_S:.0f}s)",
        )

    # -- audio --------------------------------------------------------------

    def _audio(self, spec: VideoSpec) -> list[QCCheck]:
        a = spec.audio
        out: list[QCCheck] = []

        # Loudness normalisation toward the platform target.
        off = abs(a.integrated_lufs - TARGET_LUFS)
        out.append(QCCheck(
            name="loudness",
            status=CheckStatus.PASS if off <= LUFS_TOLERANCE else CheckStatus.WARN,
            detail=f"{a.integrated_lufs:.1f} LUFS (target {TARGET_LUFS:.0f}±{LUFS_TOLERANCE:.0f})",
        ))

        # No clipping — true peak must stay below the ceiling.
        clip_ok = a.true_peak_db <= MAX_TRUE_PEAK_DB
        out.append(QCCheck(
            name="audio_clipping",
            status=CheckStatus.PASS if clip_ok else CheckStatus.FAIL,
            detail=f"true peak {a.true_peak_db:.1f} dBTP (max {MAX_TRUE_PEAK_DB:.0f})",
        ))

        # No overlapping narration.
        out.append(QCCheck(
            name="overlapping_narration",
            status=CheckStatus.FAIL if a.overlapping_narration else CheckStatus.PASS,
            detail="two narration tracks overlap" if a.overlapping_narration
            else "single narration",
        ))

        # Voice must sit clearly above any music bed.
        if a.music_present and a.voice_present:
            bal_ok = a.voice_over_music_db >= MIN_VOICE_OVER_MUSIC_DB
            out.append(QCCheck(
                name="voice_music_balance",
                status=CheckStatus.PASS if bal_ok else CheckStatus.FAIL,
                detail=f"voice {a.voice_over_music_db:.1f} dB over music "
                       f"(min {MIN_VOICE_OVER_MUSIC_DB:.0f})",
            ))

        # Unlicensed music is a hard copyright stop.
        if a.music_present:
            out.append(QCCheck(
                name="music_licence",
                status=CheckStatus.PASS if a.music_licensed else CheckStatus.FAIL,
                detail="licensed/cleared" if a.music_licensed
                else "music not cleared — copyright risk",
            ))

        return out

    # -- captions -----------------------------------------------------------

    def _captions(self, spec: VideoSpec) -> list[QCCheck]:
        cues = sorted(spec.captions, key=lambda c: c.start)
        out: list[QCCheck] = []

        # Structurally valid subtitles (not "broken").
        broken = [
            c for c in cues
            if c.end <= c.start or c.start < 0 or c.end > spec.duration_s + 0.05
        ]
        out.append(QCCheck(
            name="subtitles_valid",
            status=CheckStatus.FAIL if broken else CheckStatus.PASS,
            detail=f"{len(broken)} broken cue(s)" if broken
            else f"{len(cues)} cue(s) within bounds",
        ))

        if cues:
            # Timing: no overlap between consecutive cues, none too short/long.
            pairs = list(zip(cues, cues[1:], strict=False))
            overlaps = sum(1 for a, b in pairs if b.start < a.end - 1e-6)
            bad_len = [c for c in cues if c.duration < MIN_CUE_S or c.duration > MAX_CUE_S]
            timing_ok = overlaps == 0 and not bad_len
            out.append(QCCheck(
                name="caption_timing",
                status=CheckStatus.PASS if timing_ok else CheckStatus.FAIL,
                detail=f"{overlaps} overlap(s), {len(bad_len)} mistimed cue(s)",
            ))

            # No duplicated captions (same text back-to-back).
            dups = sum(
                1 for a, b in pairs
                if a.text.strip().lower() == b.text.strip().lower() and a.text.strip()
            )
            out.append(QCCheck(
                name="caption_duplication",
                status=CheckStatus.FAIL if dups else CheckStatus.PASS,
                detail=f"{dups} duplicated cue(s)" if dups else "no duplicates",
            ))

        return out

    def _caption_accuracy(self, spec: VideoSpec) -> QCCheck:
        if not spec.transcript or not spec.captions:
            return QCCheck(name="caption_accuracy", status=CheckStatus.PASS,
                           detail="no transcript to compare")
        spoken = _tokens(spec.transcript)
        captioned = set(_tokens(" ".join(c.text for c in spec.captions)))
        if not spoken:
            return QCCheck(name="caption_accuracy", status=CheckStatus.PASS,
                           detail="empty transcript")
        covered = sum(1 for t in spoken if t in captioned) / len(spoken)
        ok = covered >= MIN_CAPTION_ACCURACY
        return QCCheck(
            name="caption_accuracy",
            status=CheckStatus.PASS if ok else CheckStatus.FAIL,
            detail=f"{covered:.0%} of spoken words captioned (min {MIN_CAPTION_ACCURACY:.0%})",
        )

    # -- generation-model licence (commercial-use gate) ---------------------

    def _model_licence(self, spec: VideoSpec) -> QCCheck:
        if not spec.generation_models:
            return QCCheck(name="model_licence", status=CheckStatus.PASS,
                           detail="no generation models declared")
        verdict = licence_check(spec.generation_models, commercial=spec.commercial_use)
        if verdict.passed:
            note = "; ".join(verdict.notes) if verdict.notes else "all models cleared"
            return QCCheck(name="model_licence", status=CheckStatus.PASS,
                           detail=f"cleared: {', '.join(verdict.cleared)} — {note}".strip(" —"))
        problems = verdict.blocked + [f"{u} (unregistered)" for u in verdict.unknown]
        return QCCheck(name="model_licence", status=CheckStatus.FAIL,
                       detail="not cleared for commercial use: " + ", ".join(problems))

    # -- visual (the headline: obstruction + safe area + readability) -------

    def _visual(self, spec: VideoSpec) -> list[QCCheck]:
        out: list[QCCheck] = []
        template = get_template(spec.platform, spec.surface)
        protected_visual = [r.to_region() for r in spec.regions if r.kind in _PROTECTED_VISUAL]
        protected_text = [r.to_region() for r in spec.regions if r.kind in _PROTECTED_TEXT]
        boxes = [b.to_box() for b in spec.caption_boxes] + [b.to_box() for b in spec.overlays]

        if template is None:
            out.append(QCCheck(
                name="safe_area", status=CheckStatus.WARN,
                detail=f"no template for {spec.platform.value}/{spec.surface.value}"))
        else:
            exclusion_names = {z.name for z in template.exclusions}
            obstruction_hits: list[str] = []
            text_hits: list[str] = []
            edge_hits = 0
            ui_hits: list[str] = []
            for box in boxes:
                # Faces / objects / logos — edge + UI are read from this pass.
                pv = self.layout.check_overlay(template, box, regions=protected_visual)
                if not pv.ok:
                    for blocker in pv.blocked_by:
                        if blocker == "title_safe_edge":
                            edge_hits += 1
                        elif blocker in exclusion_names:
                            ui_hits.append(blocker)
                        else:
                            obstruction_hits.append(blocker)
                # On-screen text — region blockers only (edge/UI already counted).
                pt = self.layout.check_overlay(template, box, regions=protected_text)
                if not pt.ok:
                    for blocker in pt.blocked_by:
                        if blocker != "title_safe_edge" and blocker not in exclusion_names:
                            text_hits.append(blocker)

            # No captions covering faces / objects / logos.
            out.append(QCCheck(
                name="visual_obstruction",
                status=CheckStatus.FAIL if obstruction_hits else CheckStatus.PASS,
                detail=("covers " + ", ".join(sorted(set(obstruction_hits)))) if obstruction_hits
                else "captions/overlays clear of faces, objects and logos",
            ))
            # No captions overlapping existing on-screen text.
            out.append(QCCheck(
                name="text_overlap",
                status=CheckStatus.FAIL if text_hits else CheckStatus.PASS,
                detail=("overlaps " + ", ".join(sorted(set(text_hits)))) if text_hits
                else "captions/overlays clear of on-screen text",
            ))
            # Nothing under the platform UI.
            out.append(QCCheck(
                name="platform_ui_clear",
                status=CheckStatus.FAIL if ui_hits else CheckStatus.PASS,
                detail=("collides with " + ", ".join(sorted(set(ui_hits)))) if ui_hits
                else "clear of platform UI zones",
            ))
            # No text too close to the screen edge.
            out.append(QCCheck(
                name="edge_safe",
                status=CheckStatus.FAIL if edge_hits else CheckStatus.PASS,
                detail=f"{edge_hits} element(s) outside title-safe" if edge_hits
                else "all elements inside title-safe",
            ))

        # No blurry output.
        out.append(QCCheck(
            name="sharpness",
            status=CheckStatus.PASS if spec.sharpness >= MIN_SHARPNESS else CheckStatus.FAIL,
            detail=f"sharpness {spec.sharpness:.2f} (min {MIN_SHARPNESS:.2f})",
        ))
        # No visual clutter.
        out.append(QCCheck(
            name="visual_clutter",
            status=CheckStatus.PASS if spec.clutter <= MAX_CLUTTER else CheckStatus.WARN,
            detail=f"clutter {spec.clutter:.2f} (max {MAX_CLUTTER:.2f})",
        ))
        return out
