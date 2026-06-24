"""Performance & success-metric models.

These mirror the success metrics named in the platform directive. The Algorithm
Watchtower ingests :class:`PerformanceSignal` rows and feeds learning back into
``INVISABLE_BRAIN``.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class SuccessMetric(StrEnum):
    """The metrics the platform is graded on (see the directive)."""

    FOLLOWER_GROWTH = "follower_growth"
    PROFILE_VISITS = "profile_visits"
    WATCH_TIME = "watch_time"
    RETENTION = "retention"
    SHARES = "shares"
    SAVES = "saves"
    COMMENTS = "comments"
    STORY_SUBMISSIONS = "story_submissions"
    WEBSITE_VISITS = "website_visits"
    MEDIA_MENTIONS = "media_mentions"
    PODCAST_INVITATIONS = "podcast_invitations"
    SPEAKING_OPPORTUNITIES = "speaking_opportunities"
    PARTNER_ENQUIRIES = "partner_enquiries"
    SPONSOR_ENQUIRIES = "sponsor_enquiries"
    FOUNDER_RECOGNITION_INDEX = "founder_recognition_index"


class PerformanceSignal(BaseModel):
    """One observed datapoint for a published piece of content."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    candidate_id: str
    platform: str
    metric: SuccessMetric
    value: float
    # Free-form context the Watchtower can correlate against later.
    themes: list[str] = Field(default_factory=list)
    founder_centred: bool = False
    observed_at: str | None = None  # ISO-8601; supplied by the caller / DB default
