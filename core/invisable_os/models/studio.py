"""Studio domain models.

The :class:`StudioPost` is the atom the **5090 Studio Engine** moves around. Unlike a
raw :class:`~invisable_os.models.content.ContentCandidate` (a generation scaffold), a
StudioPost is a *fully-formed, reviewable, exportable* piece — caption, hashtags,
script, visual idea and founder-presence suggestion already attached, plus the four
editorial scores a human reviews on at a glance: risk, mission, humour, authenticity.

Everything here is offline-first: a StudioPost is plain data that serialises to JSON
and saves to a local folder, so the Studio app works with no server, no PWA backend,
and no social-platform connection.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field

from invisable_os.models.content import ContentFormat, Platform


class StudioStatus(StrEnum):
    """Where a StudioPost sits in the local review lifecycle.

    The values double as the export sub-folder names under the studio root:
    ``generated`` / ``approved`` / ``rejected`` / ``ready_to_post``.
    """

    GENERATED = "generated"  # freshly produced, awaiting human review
    APPROVED = "approved"  # the founder/editor approved it locally
    REJECTED = "rejected"  # rejected locally — kept so the studio learns
    READY_TO_POST = "ready_to_post"  # exported, packaged for posting by hand


class StudioScores(BaseModel):
    """The four at-a-glance editorial scores, each 0.0–1.0.

    ``risk`` is the only one where *lower is better* (0 = safe, 1 = blocked/high
    risk). The other three reward the content: mission alignment, humour, and
    authenticity.
    """

    risk: float = Field(default=0.0, ge=0.0, le=1.0)
    mission: float = Field(default=0.0, ge=0.0, le=1.0)
    humour: float = Field(default=0.0, ge=0.0, le=1.0)
    authenticity: float = Field(default=0.0, ge=0.0, le=1.0)


class StudioPost(BaseModel):
    """A complete, reviewable, exportable piece of content produced locally."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    batch: str = Field(default="", description="Which batch produced it (e.g. daily20, humour).")
    pillar: str = Field(default="", description="Content pillar: humour/education/founder/…")
    status: StudioStatus = StudioStatus.GENERATED

    # --- the post itself ----------------------------------------------------
    platform: Platform = Platform.INSTAGRAM
    format: ContentFormat = ContentFormat.SHORT_VIDEO
    hook: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    script: str = Field(default="", description="Shot-by-shot / beat-by-beat script.")
    visual_idea: str = Field(default="", description="What to film or design.")
    founder_presence_suggestion: str = Field(
        default="", description="How (or whether) to put Stephen on camera/voice."
    )

    # --- the four editorial scores -----------------------------------------
    scores: StudioScores = Field(default_factory=StudioScores)

    # --- provenance & ethics -----------------------------------------------
    founder_centred: bool = False
    original: bool = True
    themes: list[str] = Field(default_factory=list)
    generator: str = Field(default="stub", description="Model/engine that produced it.")
    rationale: str = Field(default="", description="Why it scored the way it did.")
    needs_human_review: bool = Field(
        default=False, description="Passed the gate but carries an advisory risk flag."
    )
    notes: list[str] = Field(default_factory=list)
    created_at: str = Field(default="", description="ISO timestamp, set when saved.")

    # Convenience score accessors so callers/tests don't reach through .scores.
    @property
    def risk_score(self) -> float:
        return self.scores.risk

    @property
    def mission_score(self) -> float:
        return self.scores.mission

    @property
    def humour_score(self) -> float:
        return self.scores.humour

    @property
    def authenticity_score(self) -> float:
        return self.scores.authenticity
