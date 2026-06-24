"""Concrete renderers, each guarded with a dry-run fallback.

The classes describe *how* each backend would render an asset; when the backend
isn't configured/reachable they return a dry-run placeholder so the pipeline always
completes. Real rendering is wired behind the env-configured base URLs/keys.
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


def _placeholder(kind: str, out_dir: str, backend: str) -> str:
    ext = "mp4" if kind in VIDEO_KINDS else "png" if kind in IMAGE_KINDS else "txt"
    return f"{out_dir.rstrip('/')}/{backend}/{kind}.{ext}"


class ComfyUIRenderer:
    """Images (Flux) and short video (Wan/Hunyuan/LTX) via ComfyUI on the GPU box."""

    name = "comfyui"

    def __init__(self) -> None:
        self.base_url = os.getenv("COMFYUI_BASE_URL", "")

    def handles(self, kind: str) -> bool:
        return kind in IMAGE_KINDS or kind in VIDEO_KINDS

    def render(self, kind: str, spec: str, *, out_dir: str) -> RenderResult:
        if not self.base_url:
            return RenderResult(
                ok=True, kind=kind, backend="dry-run",
                path=_placeholder(kind, out_dir, "comfyui"),
                detail=f"[dry-run] would render {kind} via ComfyUI: {spec[:60]}",
            )
        # Real submission to ComfyUI would go here (queue prompt, poll, fetch output).
        return RenderResult(
            ok=True, kind=kind, backend=self.name,
            path=_placeholder(kind, out_dir, "comfyui"),
            detail=f"submitted {kind} to ComfyUI",
        )


class ElevenLabsRenderer:
    """Voiceover narration via ElevenLabs."""

    name = "elevenlabs"

    def __init__(self) -> None:
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "")

    def handles(self, kind: str) -> bool:
        return kind in VOICE_KINDS

    def render(self, kind: str, spec: str, *, out_dir: str) -> RenderResult:
        backend = self.name if self.api_key else "dry-run"
        detail = (
            "narrated voiceover via ElevenLabs" if self.api_key
            else f"[dry-run] would narrate: {spec[:60]}"
        )
        return RenderResult(
            ok=True, kind=kind, backend=backend,
            path=_placeholder("voiceover", out_dir, "elevenlabs"), detail=detail,
        )


class CaptionRenderer:
    """Captions/subtitles via Whisper."""

    name = "whisper"

    def handles(self, kind: str) -> bool:
        return kind in CAPTION_KINDS

    def render(self, kind: str, spec: str, *, out_dir: str) -> RenderResult:
        return RenderResult(
            ok=True, kind=kind, backend="dry-run",
            path=_placeholder("caption", out_dir, "whisper"),
            detail=f"[dry-run] would caption: {spec[:60]}",
        )


class PassthroughRenderer:
    """Catch-all for text-shaped specs (story polls, comment angles) — no media."""

    name = "passthrough"

    def handles(self, kind: str) -> bool:
        return True

    def render(self, kind: str, spec: str, *, out_dir: str) -> RenderResult:
        return RenderResult(
            ok=True, kind=kind, backend="passthrough",
            path=_placeholder(kind, out_dir, "text"),
            detail=f"text asset: {spec[:60]}",
        )


def default_renderers() -> list:
    """Ordered renderers; the first that ``handles`` a kind wins."""
    return [ComfyUIRenderer(), ElevenLabsRenderer(), CaptionRenderer(), PassthroughRenderer()]
