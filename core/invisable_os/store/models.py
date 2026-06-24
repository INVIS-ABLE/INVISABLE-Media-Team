"""SQLAlchemy ORM models — the operational tables the app owns.

Lists are stored as portable JSON columns so the same models run on SQLite and
Postgres unchanged. These back the content lifecycle (approval queue), the fixed
tag network, partners, people/consent, opportunities, and performance signals.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String

from invisable_os.store.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class QueueItemRow(Base):
    """One piece of content moving through the lifecycle toward publication."""

    __tablename__ = "queue_item"

    id = Column(String, primary_key=True)
    candidate_id = Column(String, index=True)
    candidate = Column(JSON, nullable=False)  # full ContentCandidate dump
    status = Column(String, nullable=False, default="pending_review", index=True)
    slot_label = Column(String, default="")
    pillar = Column(String, default="", index=True)
    platform = Column(String, default="")

    weighted_total = Column(Float, default=0.0)
    mission_total = Column(Float, default=0.0)
    mission_verdict = Column(String, default="hold")
    quality_avg = Column(Float, default=0.0)
    quality_passes = Column(Boolean, default=False)
    needs_human_review = Column(Boolean, default=False)
    risk_flags = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    asset_count = Column(Integer, default=0)
    flywheel = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "candidate": self.candidate,
            "status": self.status,
            "slot_label": self.slot_label,
            "pillar": self.pillar,
            "platform": self.platform,
            "weighted_total": self.weighted_total,
            "mission_total": self.mission_total,
            "mission_verdict": self.mission_verdict,
            "quality_avg": self.quality_avg,
            "quality_passes": self.quality_passes,
            "needs_human_review": self.needs_human_review,
            "risk_flags": self.risk_flags or [],
            "tags": self.tags or [],
            "asset_count": self.asset_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


class TagMemberRow(Base):
    __tablename__ = "tag_member"

    id = Column(String, primary_key=True)
    display_name = Column(String, nullable=False)
    tiktok_handle = Column(String, nullable=True)
    instagram_handle = Column(String, nullable=True)
    category = Column(String, default="network")
    relationship = Column(String, default="")
    approved = Column(Boolean, default=True)
    paused = Column(Boolean, default=False)
    do_not_tag = Column(Boolean, default=False)
    notes = Column(String, default="")
    created_at = Column(DateTime(timezone=True), default=_now)


class PartnerRow(Base):
    __tablename__ = "partner_row"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    kind = Column(String, default="partner")
    sector = Column(String, default="")
    status = Column(String, default="active")
    last_contact = Column(String, nullable=True)
    interests = Column(JSON, default=list)
    notes = Column(String, default="")
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "sector": self.sector,
            "status": self.status,
            "last_contact": self.last_contact,
            "interests": self.interests or [],
            "notes": self.notes,
        }


class OpportunityRow(Base):
    __tablename__ = "opportunity_row"

    id = Column(String, primary_key=True)
    kind = Column(String, nullable=False)
    title = Column(String, nullable=False)
    fit_score = Column(Float, default=0.5)
    why = Column(String, default="")
    suggested_action = Column(String, default="")
    status = Column(String, default="open")
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "fit_score": self.fit_score,
            "why": self.why,
            "suggested_action": self.suggested_action,
            "status": self.status,
        }


class PerfSignalRow(Base):
    __tablename__ = "perf_signal_row"

    id = Column(String, primary_key=True)
    candidate_id = Column(String, index=True)
    platform = Column(String, default="")
    metric = Column(String, nullable=False)
    value = Column(Float, default=0.0)
    themes = Column(JSON, default=list)
    observed_at = Column(DateTime(timezone=True), default=_now)


# ============================================================================
# Scheduling — connected channels + a weekly posting-slot schedule (the
# Buffer/Postiz/Mixpost "queue" pattern: define slots once, fill the next free
# one automatically). Architecture borrowed from those tools; code is original.
# ============================================================================


class ChannelRow(Base):
    """A connected social account a post can target."""

    __tablename__ = "channel"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    handle = Column(String, default="")
    timezone = Column(String, default="Europe/London")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "handle": self.handle,
            "timezone": self.timezone,
            "active": self.active,
        }


class ScheduleSlotRow(Base):
    """A recurring weekly posting slot for a channel (weekday + time-of-day)."""

    __tablename__ = "schedule_slot"

    id = Column(String, primary_key=True)
    channel_id = Column(String, index=True)
    weekday = Column(Integer, nullable=False)  # 0=Monday … 6=Sunday
    hour = Column(Integer, nullable=False)
    minute = Column(Integer, default=0)
    active = Column(Boolean, default=True)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "weekday": self.weekday,
            "hour": self.hour,
            "minute": self.minute,
            "active": self.active,
        }


class MediaAssetRow(Base):
    """A produced media asset in the library, linked to a queue item."""

    __tablename__ = "media_asset"

    id = Column(String, primary_key=True)
    queue_item_id = Column(String, index=True)
    kind = Column(String, nullable=False)  # tiktok | reel | quote_graphic | voiceover | …
    spec = Column(String, default="")
    path = Column(String, default="")
    backend = Column(String, default="dry-run")
    status = Column(String, default="rendered")
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "queue_item_id": self.queue_item_id,
            "kind": self.kind,
            "spec": self.spec,
            "path": self.path,
            "backend": self.backend,
            "status": self.status,
        }
