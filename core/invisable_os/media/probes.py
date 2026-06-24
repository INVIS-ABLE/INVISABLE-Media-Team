"""Real probe backends for the Video Quality Gate.

The gate ([`video_qc.py`](./video_qc.py)) is pure logic over a :class:`VideoSpec`.
These probes *build* that spec from an actual file by shelling out to FFmpeg/Whisper.
Each follows the same contract as the renderers: **use the real tool when it's
installed, otherwise return the spec unchanged and mark it a dry-run** — so the
pipeline runs anywhere and only does real measurement on the GPU box.

The parsing is split out as pure functions (:func:`parse_ffprobe`,
:func:`parse_ebur128`) so it is unit-tested against captured tool output even where
the binaries aren't installed; the probe classes are thin subprocess wrappers.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess

from invisable_os.media.video_qc import CaptionCue, VideoProbe, VideoSpec

log = logging.getLogger(__name__)

_FFPROBE_TIMEOUT = 30
_FFMPEG_TIMEOUT = 120


# --- Pure parsers (unit-tested without the binaries) ------------------------


def _ratio_to_float(value: str) -> float:
    """Parse an FFmpeg rational like ``30000/1001`` or ``25/1`` to a float."""
    value = (value or "").strip()
    if "/" in value:
        num, _, den = value.partition("/")
        try:
            n, d = float(num), float(den)
            return round(n / d, 3) if d else 0.0
        except ValueError:
            return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_ffprobe(ffprobe_json: str) -> dict:
    """Pull width/height/fps/duration/has_audio from ``ffprobe -print_format json``."""
    data = json.loads(ffprobe_json)
    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    out: dict = {"has_audio": has_audio}
    if video:
        out["width"] = int(video.get("width", 0) or 0)
        out["height"] = int(video.get("height", 0) or 0)
        fps = _ratio_to_float(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0")
        out["fps"] = fps
    duration = fmt.get("duration") or (video or {}).get("duration")
    if duration is not None:
        try:
            out["duration_s"] = round(float(duration), 3)
        except ValueError:
            pass
    return out


def parse_ebur128(stderr: str) -> dict:
    """Pull integrated loudness + true peak from ``ffmpeg -af ebur128=peak=true``.

    FFmpeg prints a summary block on stderr ending with lines like::

        Integrated loudness:
          I:         -14.0 LUFS
        ...
        True peak:
          Peak:       -1.0 dBFS
    """
    integrated: float | None = None
    true_peak: float | None = None
    for raw in stderr.splitlines():
        line = raw.strip()
        if line.startswith("I:") and "LUFS" in line:
            integrated = _first_float(line)
        elif line.startswith("Peak:") and ("dBFS" in line or "dB" in line):
            true_peak = _first_float(line)
    out: dict = {}
    if integrated is not None:
        out["integrated_lufs"] = integrated
    if true_peak is not None:
        out["true_peak_db"] = true_peak
    return out


def _first_float(text: str) -> float | None:
    for token in text.replace(":", " ").split():
        try:
            return float(token)
        except ValueError:
            continue
    return None


# --- FFmpeg probe -----------------------------------------------------------


def _default_ffprobe(path: str) -> str:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True, timeout=_FFPROBE_TIMEOUT, check=True,
    )
    return result.stdout


def _default_ebur128(path: str) -> str:
    # ebur128 prints its summary to stderr; a null muxer avoids writing output.
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, timeout=_FFMPEG_TIMEOUT, check=False,
    )
    return result.stderr


class FFmpegProbe:
    """Container metadata (ffprobe) + loudness/true-peak (ffmpeg ebur128).

    Follows the :class:`~invisable_os.media.assembly.VideoAssembler` idiom: the tool
    runners are injectable and ``force_available`` bypasses the binary check, so the
    real parsing/merging path is unit-testable without FFmpeg installed.
    """

    name = "ffmpeg"

    def __init__(
        self,
        ffprobe_runner=None,
        ebur128_runner=None,
        *,
        force_available: bool = False,
    ) -> None:
        self._ffprobe = ffprobe_runner or _default_ffprobe
        self._ebur128 = ebur128_runner or _default_ebur128
        self._force = force_available

    @property
    def available(self) -> bool:
        return self._force or shutil.which("ffprobe") is not None

    def probe(self, path: str, spec: VideoSpec) -> VideoSpec:
        if not self.available:
            log.info("ffprobe not found; FFmpegProbe dry-run for %s", path)
            return spec.model_copy(update={"probe_backend": "dry-run"})

        updates: dict = {"probe_backend": self.name}
        try:
            meta = parse_ffprobe(self._ffprobe(path))
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            log.warning("ffprobe failed for %s: %s", path, exc)
            return spec.model_copy(update={"probe_backend": "dry-run"})

        has_audio = meta.pop("has_audio", None)
        updates.update({k: v for k, v in meta.items() if v})

        # Loudness only when ffmpeg is present and there's an audio track.
        if has_audio and (self._force or shutil.which("ffmpeg")):
            try:
                stats = parse_ebur128(self._ebur128(path))
                if stats:
                    updates["audio"] = spec.audio.model_copy(update=stats)
            except (subprocess.SubprocessError, OSError) as exc:
                log.warning("ebur128 failed for %s: %s", path, exc)
        return spec.model_copy(update=updates)


# --- Whisper probe ----------------------------------------------------------


class WhisperProbe:
    """Transcript + caption cues via faster-whisper (falls back to dry-run)."""

    name = "whisper"

    def __init__(self, model_size: str = "base") -> None:
        self.model_size = model_size

    @property
    def available(self) -> bool:
        return importlib_available("faster_whisper")

    def probe(self, path: str, spec: VideoSpec) -> VideoSpec:
        if not self.available:
            log.info("faster_whisper not installed; WhisperProbe dry-run for %s", path)
            return spec
        try:
            from faster_whisper import WhisperModel  # type: ignore

            model = WhisperModel(self.model_size)
            segments, _info = model.transcribe(path)
            cues = [
                CaptionCue(start=round(s.start, 3), end=round(s.end, 3), text=s.text.strip())
                for s in segments
            ]
        except Exception as exc:  # noqa: BLE001 — never let transcription crash the pipeline
            log.warning("whisper transcription failed for %s: %s", path, exc)
            return spec
        transcript = " ".join(c.text for c in cues).strip()
        return spec.model_copy(update={"captions": cues, "transcript": transcript})


def importlib_available(module: str) -> bool:
    """True if ``module`` can be imported (without importing it)."""
    import importlib.util

    return importlib.util.find_spec(module) is not None


# --- Orchestration ----------------------------------------------------------


def default_probes() -> list[VideoProbe]:
    """The probes run, in order, to enrich a spec from a file."""
    return [FFmpegProbe(), WhisperProbe()]


def probe_video(
    path: str,
    spec: VideoSpec | None = None,
    probes: list[VideoProbe] | None = None,
) -> VideoSpec:
    """Build/enrich a :class:`VideoSpec` for ``path`` by running each probe in turn.

    Pass an existing ``spec`` to carry annotations the probes can't infer (platform,
    surface, detected regions, music licence). Returns a spec ready for the gate.
    """
    spec = spec or VideoSpec()
    for probe in probes or default_probes():
        spec = probe.probe(path, spec)
    return spec
