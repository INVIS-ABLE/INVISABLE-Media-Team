"""Concrete renderers.

In **live** mode each renderer calls its real backend and writes an actual file; on
any failure (or when the backend isn't configured) it falls back to a **dry-run**
placeholder so the pipeline always completes. Offline / GPU-less, everything is
dry-run and writes nothing — keeping the platform testable and side-effect-free.
"""

from __future__ import annotations

import logging
import os

from invisable_os.media.base import RenderResult

log = logging.getLogger(__name__)

# Which asset kinds each backend is responsible for.
IMAGE_KINDS = {"quote_graphic", "image", "carousel"}
VIDEO_KINDS = {"tiktok", "reel"}
VOICE_KINDS = {"voiceover"}
CAPTION_KINDS = {"caption", "captions"}
TEXT_KINDS = {"story_poll", "comment_response"}


def _ext(kind: str) -> str:
    if kind in VIDEO_KINDS:
        return "mp4"
    if kind in IMAGE_KINDS:
        return "png"
    if kind in VOICE_KINDS:
        return "mp3"
    if kind in CAPTION_KINDS:
        return "srt"
    return "txt"


def _out_path(kind: str, out_dir: str, backend: str) -> str:
    return f"{out_dir.rstrip('/')}/{backend}/{kind}.{_ext(kind)}"


def _dry(kind: str, out_dir: str, what: str) -> RenderResult:
    return RenderResult(
        ok=True, kind=kind, backend="dry-run",
        path=_out_path(kind, out_dir, "dry-run"),
        detail=f"[dry-run] would {what}",
    )


class ComfyUIRenderer:
    """Images (Flux) and short video (Wan/Hunyuan/LTX) via ComfyUI on the GPU box."""

    name = "comfyui"

    def __init__(self) -> None:
        self.base_url = os.getenv("COMFYUI_BASE_URL", "")

    def handles(self, kind: str) -> bool:
        return kind in IMAGE_KINDS or kind in VIDEO_KINDS

    def render(self, kind: str, spec: str, *, out_dir: str, live: bool = False) -> RenderResult:
        if not (live and self.base_url):
            return _dry(kind, out_dir, f"render {kind} via ComfyUI: {spec[:60]}")
        try:
            from invisable_os.media.comfyui import ComfyUIClient

            size = int(os.getenv("COMFYUI_IMAGE_SIZE", "1024"))
            path = _out_path(kind, out_dir, self.name)
            ComfyUIClient(self.base_url).generate(spec, path, width=size, height=size)
            return RenderResult(ok=True, kind=kind, backend=self.name, path=path, detail="rendered")
        except Exception as exc:  # noqa: BLE001 — never break the pipeline
            log.warning("ComfyUI render failed, dry-run fallback: %s", exc)
            return _dry(kind, out_dir, f"render {kind} (ComfyUI error: {exc})")


class ElevenLabsRenderer:
    """Voiceover narration via ElevenLabs."""

    name = "elevenlabs"

    def __init__(self) -> None:
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "")

    def handles(self, kind: str) -> bool:
        return kind in VOICE_KINDS

    def render(self, kind: str, spec: str, *, out_dir: str, live: bool = False) -> RenderResult:
        if not (live and self.api_key):
            return _dry(kind, out_dir, f"narrate: {spec[:60]}")
        try:
            from invisable_os.media.elevenlabs import ElevenLabsClient

            path = _out_path(kind, out_dir, self.name)
            ElevenLabsClient(self.api_key).synthesize(spec, path)
            return RenderResult(ok=True, kind=kind, backend=self.name, path=path, detail="narrated")
        except Exception as exc:  # noqa: BLE001
            log.warning("ElevenLabs render failed, dry-run fallback: %s", exc)
            return _dry(kind, out_dir, f"narrate (ElevenLabs error: {exc})")


class CaptionRenderer:
    """Captions/subtitles — a real SRT written from the script (Whisper optional)."""

    name = "captions"

    def handles(self, kind: str) -> bool:
        return kind in CAPTION_KINDS

    def render(self, kind: str, spec: str, *, out_dir: str, live: bool = False) -> RenderResult:
        if not live:
            return _dry(kind, out_dir, f"caption: {spec[:60]}")
        try:
            from invisable_os.media.captions import write_captions

            path = _out_path(kind, out_dir, self.name)
            write_captions(spec, path)
            return RenderResult(
                ok=True, kind=kind, backend=self.name, path=path, detail="captioned"
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Caption render failed, dry-run fallback: %s", exc)
            return _dry(kind, out_dir, f"caption (error: {exc})")


class PassthroughRenderer:
    """Catch-all for text-shaped specs (story polls, comment angles)."""

    name = "passthrough"

    def handles(self, kind: str) -> bool:
        return True

    def render(self, kind: str, spec: str, *, out_dir: str, live: bool = False) -> RenderResult:
        if not live:
            return _dry(kind, out_dir, f"write {kind} text")
        try:
            from invisable_os.media.fsutil import write_text

            path = _out_path(kind, out_dir, self.name)
            write_text(path, spec)
            return RenderResult(
                ok=True, kind=kind, backend=self.name, path=path, detail="text asset"
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Text render failed, dry-run fallback: %s", exc)
            return _dry(kind, out_dir, f"write {kind} text (error: {exc})")


def default_renderers() -> list:
    """Ordered renderers; the first that ``handles`` a kind wins."""
    return [ComfyUIRenderer(), ElevenLabsRenderer(), CaptionRenderer(), PassthroughRenderer()]
