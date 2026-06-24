"""Renderer protocol and shared types for the media pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class RenderResult:
    ok: bool
    kind: str
    backend: str
    path: str
    detail: str = ""


@runtime_checkable
class Renderer(Protocol):
    """Renders one asset kind from a spec."""

    name: str

    def handles(self, kind: str) -> bool: ...

    def render(self, kind: str, spec: str, *, out_dir: str, live: bool = False) -> RenderResult: ...
