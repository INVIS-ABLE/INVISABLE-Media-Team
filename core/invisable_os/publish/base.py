"""Publisher protocol and the default dry-run implementation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

log = logging.getLogger(__name__)


@dataclass
class PublishResult:
    ok: bool
    backend: str
    external_id: str | None = None
    detail: str = ""


@runtime_checkable
class Publisher(Protocol):
    """Anything that can take an approved queue item live."""

    name: str

    def publish(self, item: dict) -> PublishResult: ...


class DryRunPublisher:
    """Logs what *would* be published. The safe default — never posts anything."""

    name = "dry-run"

    def publish(self, item: dict) -> PublishResult:
        candidate = item.get("candidate", {})
        hook = candidate.get("hook", "")
        platform = item.get("platform", "?")
        log.info("[dry-run] would publish to %s: %s", platform, hook)
        return PublishResult(
            ok=True,
            backend=self.name,
            external_id=f"dryrun-{item.get('id', '')[:8]}",
            detail=f"dry-run: {platform} — {hook[:60]}",
        )
