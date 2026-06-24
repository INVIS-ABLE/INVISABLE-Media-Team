"""MediaProducer — renders a queue item's flywheel assets into the media library.

Reconstructs the Content Flywheel for a queue item's candidate, renders each asset
spec with the first capable renderer, and (optionally) records each result in the
media library so it appears against the post in the dashboard.
"""

from __future__ import annotations

from invisable_os.engines.flywheel import ContentFlywheel
from invisable_os.media.base import Renderer, RenderResult
from invisable_os.media.renderers import default_renderers
from invisable_os.models.content import ContentCandidate


class MediaProducer:
    def __init__(
        self,
        renderers: list[Renderer] | None = None,
        out_dir: str = "data/assets/generated",
    ) -> None:
        self.renderers = renderers or default_renderers()
        self.out_dir = out_dir

    def _render(self, kind: str, spec: str) -> RenderResult:
        for renderer in self.renderers:
            if renderer.handles(kind):
                return renderer.render(kind, spec, out_dir=self.out_dir)
        # default_renderers always ends with a passthrough, so this is unreachable.
        return RenderResult(ok=False, kind=kind, backend="none", path="", detail="no renderer")

    def produce(self, candidate: ContentCandidate) -> list[RenderResult]:
        """Render every flywheel asset for a candidate."""
        flywheel = ContentFlywheel().spin(candidate)
        results: list[RenderResult] = []
        for asset in flywheel.assets:
            results.append(self._render(asset.kind, asset.brief))
        return results
