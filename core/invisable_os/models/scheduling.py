"""Scheduling domain models — channels and weekly posting slots."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from invisable_os.models.content import Platform


class Channel(BaseModel):
    """A connected social account a post can target."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    platform: Platform
    handle: str = ""
    timezone: str = "Europe/London"
    active: bool = True


class ScheduleSlot(BaseModel):
    """A recurring weekly posting slot (weekday + time-of-day) for a channel."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    channel_id: str
    weekday: int = Field(ge=0, le=6, description="0=Monday … 6=Sunday")
    hour: int = Field(ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    active: bool = True
