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
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Remix, Parody & Trend Intelligence department
# ============================================================================


class ScannerSourceRow(Base):
    """A feed/source the scanner monitors (scanner_sources)."""

    __tablename__ = "scanner_source"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, default="rss")  # rss | trends | forum | search | research
    url = Column(String, default="")
    topic_area = Column(String, default="", index=True)
    platform = Column(String, default="")
    scan_frequency = Column(String, default="daily")
    enabled = Column(Boolean, default=True)
    notes = Column(String, default="")
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "url": self.url,
            "topic_area": self.topic_area,
            "platform": self.platform,
            "scan_frequency": self.scan_frequency,
            "enabled": self.enabled,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScannedItemRow(Base):
    """An abstracted scanned trend/reference (scanned_items)."""

    __tablename__ = "scanned_item"

    id = Column(String, primary_key=True)
    source_id = Column(String, default="", index=True)
    url = Column(String, default="")
    title = Column(String, nullable=False)
    creator = Column(String, default="")
    platform = Column(String, default="")
    summary = Column(String, default="")
    transcript = Column(String, default="")
    topic_tags = Column(JSON, default=list)
    trend_score = Column(Float, default=0.0)
    humour_score = Column(Float, default=0.0)
    construction_score = Column(Float, default=0.0)
    invisible_illness_score = Column(Float, default=0.0)
    sponsor_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    rights_status = Column(String, default="reference_only", index=True)
    status = Column(String, default="new", index=True)  # new | actioned | dismissed
    date_found = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "creator": self.creator,
            "platform": self.platform,
            "summary": self.summary,
            "transcript": self.transcript,
            "topic_tags": self.topic_tags or [],
            "trend_score": self.trend_score,
            "humour_score": self.humour_score,
            "construction_score": self.construction_score,
            "invisible_illness_score": self.invisible_illness_score,
            "sponsor_score": self.sponsor_score,
            "risk_score": self.risk_score,
            "rights_status": self.rights_status,
            "status": self.status,
            "date_found": self.date_found.isoformat() if self.date_found else None,
        }


class RightsAssetRow(Base):
    """A media asset with rights/consent metadata — the rights manager library.

    Distinct from :class:`MediaAssetRow` (the produced-media pipeline): this is the
    rights-classified source/library asset that gates whether footage may be reused.
    """

    __tablename__ = "media_assets"

    id = Column(String, primary_key=True)
    file_path = Column(String, default="")
    source_url = Column(String, default="")
    title = Column(String, default="")
    asset_type = Column(String, default="video")  # video | audio | image | voice | broll
    owner = Column(String, default="")
    rights_status = Column(String, default="owned", index=True)
    licence_notes = Column(String, default="")
    consent_id = Column(String, default="")
    expiry_date = Column(String, nullable=True)
    allowed_platforms = Column(JSON, default=list)
    allowed_uses = Column(JSON, default=list)
    blocked_uses = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "source_url": self.source_url,
            "title": self.title,
            "asset_type": self.asset_type,
            "owner": self.owner,
            "rights_status": self.rights_status,
            "licence_notes": self.licence_notes,
            "consent_id": self.consent_id,
            "expiry_date": self.expiry_date,
            "allowed_platforms": self.allowed_platforms or [],
            "allowed_uses": self.allowed_uses or [],
            "blocked_uses": self.blocked_uses or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PopCultureRow(Base):
    """A pop-culture reference (pop_culture_references)."""

    __tablename__ = "pop_culture_reference"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    source_type = Column(String, default="film")
    reference_description = Column(String, default="")
    exact_quote = Column(String, default="")
    paraphrase_safe_version = Column(String, default="")
    tone = Column(String, default="")
    humour_style = Column(String, default="")
    copyright_risk = Column(String, default="medium")
    use_allowed = Column(Boolean, default=True)
    suggested_invisable_angle = Column(String, default="")
    platforms = Column(JSON, default=list)
    related_topics = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source_type": self.source_type,
            "reference_description": self.reference_description,
            "exact_quote": self.exact_quote,
            "paraphrase_safe_version": self.paraphrase_safe_version,
            "tone": self.tone,
            "humour_style": self.humour_style,
            "copyright_risk": self.copyright_risk,
            "use_allowed": self.use_allowed,
            "suggested_invisable_angle": self.suggested_invisable_angle,
            "platforms": self.platforms or [],
            "related_topics": self.related_topics or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MemeFormatRow(Base):
    """A reusable meme/format template (meme_formats)."""

    __tablename__ = "meme_format"

    id = Column(String, primary_key=True)
    format_name = Column(String, nullable=False)
    description = Column(String, default="")
    structure = Column(String, default="")
    example_safe_version = Column(String, default="")
    platform = Column(String, default="")
    humour_style = Column(String, default="")
    risk_score = Column(Float, default=0.0)
    related_topics = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "format_name": self.format_name,
            "description": self.description,
            "structure": self.structure,
            "example_safe_version": self.example_safe_version,
            "platform": self.platform,
            "humour_style": self.humour_style,
            "risk_score": self.risk_score,
            "related_topics": self.related_topics or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RemixJobRow(Base):
    """A remix/parody/voiceover job moving toward approval (remix_jobs)."""

    __tablename__ = "remix_job"

    id = Column(String, primary_key=True)
    input_topic = Column(String, default="")
    reference_item_id = Column(String, default="")
    asset_id = Column(String, default="")
    output_type = Column(String, default="parody")  # parody | reaction | voiceover | meme
    mode = Column(String, default="create_parody")
    script = Column(String, default="")
    voiceover_script = Column(String, default="")
    caption = Column(String, default="")
    hashtags = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    platform = Column(String, default="")
    rights_check_status = Column(String, default="pending")  # pending | passed | failed
    brand_check_status = Column(String, default="pending")
    approval_status = Column(String, default="pending_review")
    risk_score = Column(Float, default=0.0)
    pack = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "input_topic": self.input_topic,
            "reference_item_id": self.reference_item_id,
            "asset_id": self.asset_id,
            "output_type": self.output_type,
            "mode": self.mode,
            "script": self.script,
            "voiceover_script": self.voiceover_script,
            "caption": self.caption,
            "hashtags": self.hashtags or [],
            "tags": self.tags or [],
            "platform": self.platform,
            "rights_check_status": self.rights_check_status,
            "brand_check_status": self.brand_check_status,
            "approval_status": self.approval_status,
            "risk_score": self.risk_score,
            "pack": self.pack or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ExtractedHookRow(Base):
    """A hook surfaced from a transcript (extracted_hooks)."""

    __tablename__ = "extracted_hook"

    id = Column(String, primary_key=True)
    scanned_item_id = Column(String, default="", index=True)
    hook_text = Column(String, default="")
    hook_type = Column(String, default="")
    platform = Column(String, default="")
    strength_score = Column(Float, default=0.0)
    adapted_invisable_version = Column(String, default="")
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "scanned_item_id": self.scanned_item_id,
            "hook_text": self.hook_text,
            "hook_type": self.hook_type,
            "platform": self.platform,
            "strength_score": self.strength_score,
            "adapted_invisable_version": self.adapted_invisable_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SubtitleRow(Base):
    """A generated subtitle track (subtitles)."""

    __tablename__ = "subtitle"

    id = Column(String, primary_key=True)
    asset_id = Column(String, default="", index=True)
    transcript = Column(String, default="")
    srt_path = Column(String, default="")
    burned_video_path = Column(String, default="")
    language = Column(String, default="en")
    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "transcript": self.transcript,
            "srt_path": self.srt_path,
            "burned_video_path": self.burned_video_path,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# CONTENT WAR CHEST — the reserve of approved, ready-to-post assets.
#
# The platform's rule is "always generate more than you publish". The War Chest
# is the durable reserve that makes that real: approved queue items are stocked
# here with a category, freshness and expiry, and the Scheduler & War Chest bot
# draws the best, non-repetitive item from it each posting slot. Reserve health
# tiers: minimum 500 · healthy 1,000 · elite 2,000+ (see services/war_chest.py).
# ============================================================================


class WarChestItemRow(Base):
    """One approved asset held in reserve, ready to be scheduled/published."""

    __tablename__ = "war_chest_item"

    id = Column(String, primary_key=True)
    queue_item_id = Column(String, index=True, default="")
    candidate_id = Column(String, default="")
    title = Column(String, default="")
    category = Column(String, default="evergreen", index=True)
    platform = Column(String, default="")
    pillar = Column(String, default="")

    evergreen = Column(Boolean, default=False)
    reserve_status = Column(String, default="ready", index=True)  # ready|used|expired|retired

    quality_score = Column(Float, default=0.0)
    mission_score = Column(Float, default=0.0)
    humour_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    freshness_score = Column(Float, default=1.0)

    tags = Column(JSON, default=list)
    payload = Column(JSON, default=dict)  # the candidate/content snapshot to post

    expiry_date = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    reuse_count = Column(Integer, default=0)
    notes = Column(String, default="")

    created_at = Column(DateTime(timezone=True), default=_now)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "queue_item_id": self.queue_item_id,
            "candidate_id": self.candidate_id,
            "title": self.title,
            "category": self.category,
            "platform": self.platform,
            "pillar": self.pillar,
            "evergreen": self.evergreen,
            "reserve_status": self.reserve_status,
            "quality_score": self.quality_score,
            "mission_score": self.mission_score,
            "humour_score": self.humour_score,
            "risk_score": self.risk_score,
            "freshness_score": self.freshness_score,
            "tags": self.tags or [],
            "payload": self.payload or {},
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "reuse_count": self.reuse_count,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
