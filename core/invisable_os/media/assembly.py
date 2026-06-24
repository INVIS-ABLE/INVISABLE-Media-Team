"""Video assembly — stitch rendered assets into a finished cutdown with FFmpeg.

This is the programmatic counterpart to OpenCut: it takes a post's already-rendered
**visual** (image or video), **voiceover** (audio), and **captions** (SRT) and
produces one finished `.mp4` ready to publish.

Like every backend in the pipeline it degrades to **dry-run** when FFmpeg isn't
installed (or the inputs aren't real files yet), so the step always completes and
stays testable. The FFmpeg command is built by a pure function so it can be unit
tested without the binary, and the executed runner is injectable.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field

from invisable_os.media.fsutil import ensure_dir

log = logging.getLogger(__name__)

VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv")
AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac")


@dataclass
class AssembleResult:
    ok: bool
    backend: str
    path: str
    detail: str = ""
    command: list[str] = field(default_factory=list)


def _is_video(path: str) -> bool:
    return path.lower().endswith(VIDEO_EXTS)


def _run_ffmpeg(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def build_command(
    *,
    visual: str,
    out_path: str,
    audio: str | None = None,
    captions: str | None = None,
    duration: int = 8,
) -> list[str]:
    """Build the FFmpeg command to assemble a finished cutdown.

    - image visual → looped into a clip (length = audio, else ``duration``);
    - video visual → used directly;
    - audio mixed in when present; captions burned in when present.
    """
    cmd = ["ffmpeg", "-y"]
    if _is_video(visual):
        cmd += ["-i", visual]
    else:
        cmd += ["-loop", "1", "-i", visual]
    if audio:
        cmd += ["-i", audio]

    if captions:
        # Burn subtitles into the video stream.
        cmd += ["-vf", f"subtitles={captions}"]

    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if not _is_video(visual):
        cmd += ["-tune", "stillimage"]

    if audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        cmd += ["-t", str(duration), "-an"]

    cmd += [out_path]
    return cmd


class VideoAssembler:
    """Assembles rendered assets into a finished video via FFmpeg (or dry-run)."""

    def __init__(self, runner=None, *, force_available: bool = False) -> None:
        self._runner = runner or _run_ffmpeg
        self._force = force_available

    @property
    def available(self) -> bool:
        return self._force or shutil.which("ffmpeg") is not None

    def assemble(
        self,
        *,
        visual: str | None,
        out_path: str,
        audio: str | None = None,
        captions: str | None = None,
        duration: int = 8,
    ) -> AssembleResult:
        # Need FFmpeg and a real visual file to do real work.
        if not (self.available and visual and os.path.isfile(visual)):
            return AssembleResult(
                ok=True, backend="dry-run", path=out_path,
                detail="[dry-run] would assemble final cutdown (FFmpeg/inputs unavailable)",
            )
        cmd = build_command(
            visual=visual, out_path=out_path, audio=audio, captions=captions, duration=duration
        )
        try:
            ensure_dir(os.path.dirname(out_path) or ".")
            self._runner(cmd)
            return AssembleResult(
                ok=True, backend="ffmpeg", path=out_path,
                detail="assembled final cutdown", command=cmd,
            )
        except Exception as exc:  # noqa: BLE001 — never break the pipeline
            log.warning("FFmpeg assembly failed, dry-run fallback: %s", exc)
            return AssembleResult(
                ok=True, backend="dry-run", path=out_path,
                detail=f"assemble error: {exc}", command=cmd,
            )
