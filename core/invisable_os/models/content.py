"""Content domain models.

A :class:`ContentCandidate` is the atom the whole platform moves around: the
Tournament Engine generates hundreds of them, scores them, improves them, and
selects the best; the Founder Engine balances them; the Watchtower learns from how
they perform once published.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class Platform(StrEnum):
    """Where a piece of content is destined to live."""

    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    X = "x"
    FACEBOOK = "facebook"
    THREADS = "threads"
    BLOG = "blog"
    NEWSLETTER = "newsletter"


class ContentFormat(StrEnum):
    """The shape of the content."""

    SHORT_VIDEO = "short_video"
    LONG_VIDEO = "long_video"
    CAROUSEL = "carousel"
    IMAGE = "image"
    TEXT_POST = "text_post"
    STORY = "story"
    ARTICLE = "article"
    COMMENT = "comment"


class ContentCandidate(BaseModel):
    """A single candidate piece of content."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    brief: str = Field(description="The intent this candidate is trying to serve.")
    platform: Platform
    content_format: ContentFormat = ContentFormat.SHORT_VIDEO

    hook: str = Field(default="", description="Opening line / scroll-stopper.")
    body: str = Field(default="", description="The main content / script / caption.")
    call_to_action: str = Field(default="")

    # Provenance & ethics ----------------------------------------------------
    founder_centred: bool = Field(
        default=False,
        description="Whether this content centres the founder (Stephen Garnham).",
    )
    original: bool = Field(
        default=True,
        description="Asserted originality. The guardrails verify this is not violated.",
    )
    source_inspiration: str | None = Field(
        default=None,
        description="If the *mechanics* were learned from public content, note it here. "
        "Learning patterns is allowed; copying is not.",
    )

    # Theme metadata used by the Cultural & Founder engines ------------------
    themes: list[str] = Field(default_factory=list)
    generator: str = Field(default="unknown", description="Which model/engine produced it.")

    @property
    def full_text(self) -> str:
        """All human-readable text concatenated — what the guardrails inspect."""
        return "\n".join(p for p in (self.hook, self.body, self.call_to_action) if p).strip()


class PublishDecision(StrEnum):
    """The terminal decision for a candidate."""

    PUBLISH = "publish"
    HOLD = "hold"  # good, but not selected this cycle
    REVISE = "revise"  # promising but needs another improvement pass
    REJECT = "reject"  # failed a hard gate
