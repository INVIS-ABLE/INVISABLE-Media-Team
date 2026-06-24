"""MediaProducer — renders a queue item's flywheel assets into the media library.

Reconstructs the Content Flywheel for a queue item's candidate and renders each
asset spec with the first capable renderer. Runs in **live** mode (writing real
files via the configured backends) when any media backend is configured, or when
``INVISABLE_MEDIA_OUT=1``; otherwise dry-run (no side effects).
"""

from __future__ import annotations

import os

from invisable_os.engines.flywheel import ContentFlywheel
from invisable_os.media.base import Renderer, RenderResult
from invisable_os.media.fsutil import slug
from invisable_os.media.renderers import default_renderers
from invisable_os.models.content import ContentCandidate


def _auto_live() -> bool:
    return bool(
        os.getenv("COMFYUI_BASE_URL")
        or os.getenv("ELEVENLABS_API_KEY")
        or os.getenv("INVISABLE_MEDIA_OUT")
    )


class MediaProducer:
    def __init__(
        self,
        renderers: list[Renderer] | None = None,
        out_dir: str = "data/assets/generated",
        live: bool | None = None,
    ) -> None:
        self.renderers = renderers or default_renderers()
        self.out_dir = out_dir
        self.live = _auto_live() if live is None else live

    def _render(self, kind: str, spec: str, out_dir: str) -> RenderResult:
        for renderer in self.renderers:
            if renderer.handles(kind):
                return renderer.render(kind, spec, out_dir=out_dir, live=self.live)
        # default_renderers always ends with a passthrough, so this is unreachable.
        return RenderResult(ok=False, kind=kind, backend="none", path="", detail="no renderer")

    def produce(self, candidate: ContentCandidate) -> list[RenderResult]:
        """Render every flywheel asset for a candidate."""
        flywheel = ContentFlywheel().spin(candidate)
        out_dir = f"{self.out_dir.rstrip('/')}/{slug(candidate.id)}"
        return [self._render(asset.kind, asset.brief, out_dir) for asset in flywheel.assets]
