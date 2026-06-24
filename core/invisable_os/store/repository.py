"""Repository — the high-level persistence API the rest of the platform uses.

Returns plain dicts (never live ORM objects) so callers never hit detached-instance
problems. All writes go through a transactional ``session_scope``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from invisable_os.models.content import QueueStatus
from invisable_os.models.departments import Opportunity, Partner, TagNetworkMember
from invisable_os.models.scheduling import Channel, ScheduleSlot
from invisable_os.store.db import session_scope
from invisable_os.store.models import (
    ChannelRow,
    ExtractedHookRow,
    MediaAssetRow,
    MemeFormatRow,
    OpportunityRow,
    PartnerRow,
    PerfSignalRow,
    PopCultureRow,
    QueueItemRow,
    RemixJobRow,
    RightsAssetRow,
    ScannedItemRow,
    ScannerSourceRow,
    ScheduleSlotRow,
    SourceClaimRow,
    SourceRow,
    SubtitleRow,
    TagMemberRow,
    WarChestItemRow,
)


def _now() -> datetime:
    return datetime.now(UTC)


class Repository:
    """Operational data access for the content lifecycle and departments."""

    # --- Content queue (the approval lifecycle) ----------------------------

    def enqueue(self, item: dict) -> str:
        """Persist a planned post into the queue. ``item`` is a plain dict."""
        row_id = item.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            row = QueueItemRow(
                id=row_id,
                candidate_id=item.get("candidate_id", ""),
                candidate=item.get("candidate", {}),
                status=item.get("status", QueueStatus.PENDING_REVIEW.value),
                slot_label=item.get("slot_label", ""),
                pillar=item.get("pillar", ""),
                platform=item.get("platform", ""),
                weighted_total=item.get("weighted_total", 0.0),
                mission_total=item.get("mission_total", 0.0),
                mission_verdict=item.get("mission_verdict", "hold"),
                quality_avg=item.get("quality_avg", 0.0),
                quality_passes=item.get("quality_passes", False),
                needs_human_review=item.get("needs_human_review", False),
                risk_flags=item.get("risk_flags", []),
                tags=item.get("tags", []),
                asset_count=item.get("asset_count", 0),
                flywheel=item.get("flywheel", []),
            )
            s.add(row)
        return row_id

    def list_queue(self, status: str | None = None, limit: int = 100) -> list[dict]:
        with session_scope() as s:
            stmt = select(QueueItemRow)
            if status:
                stmt = stmt.where(QueueItemRow.status == status)
            stmt = stmt.order_by(QueueItemRow.created_at.desc()).limit(limit)
            return [r.as_dict() for r in s.scalars(stmt)]

    def get_queue_item(self, item_id: str) -> dict | None:
        with session_scope() as s:
            row = s.get(QueueItemRow, item_id)
            return row.as_dict() if row else None

    def transition(self, item_id: str, status: QueueStatus, **fields) -> dict | None:
        """Move an item to a new lifecycle status, stamping timestamps."""
        with session_scope() as s:
            row = s.get(QueueItemRow, item_id)
            if row is None:
                return None
            row.status = status.value
            if status == QueueStatus.SCHEDULED:
                row.scheduled_at = _now()
            if status == QueueStatus.PUBLISHED:
                row.published_at = _now()
            for k, v in fields.items():
                setattr(row, k, v)
            return row.as_dict()

    def counts_by_status(self) -> dict[str, int]:
        with session_scope() as s:
            out: dict[str, int] = {}
            for row in s.scalars(select(QueueItemRow)):
                out[row.status] = out.get(row.status, 0) + 1
            return out

    # --- Fixed tag network --------------------------------------------------

    def add_tag_member(self, member: TagNetworkMember) -> str:
        with session_scope() as s:
            s.add(
                TagMemberRow(
                    id=member.id,
                    display_name=member.display_name,
                    tiktok_handle=member.tiktok_handle,
                    instagram_handle=member.instagram_handle,
                    category=member.category,
                    relationship=member.relationship,
                    approved=member.approved,
                    paused=member.paused,
                    do_not_tag=member.do_not_tag,
                    notes=member.notes,
                )
            )
        return member.id

    def list_tag_members(self) -> list[TagNetworkMember]:
        with session_scope() as s:
            return [
                TagNetworkMember(
                    id=r.id,
                    display_name=r.display_name,
                    tiktok_handle=r.tiktok_handle,
                    instagram_handle=r.instagram_handle,
                    category=r.category,
                    relationship=r.relationship,
                    approved=r.approved,
                    paused=r.paused,
                    do_not_tag=r.do_not_tag,
                    notes=r.notes,
                )
                for r in s.scalars(select(TagMemberRow))
            ]

    # --- Partners -----------------------------------------------------------

    def add_partner(self, partner: Partner) -> str:
        with session_scope() as s:
            s.add(
                PartnerRow(
                    id=partner.id,
                    name=partner.name,
                    kind=partner.kind,
                    sector=partner.sector,
                    status=partner.status,
                    last_contact=partner.last_contact,
                    interests=partner.interests,
                    notes=partner.notes,
                )
            )
        return partner.id

    def list_partners(self) -> list[dict]:
        with session_scope() as s:
            return [r.as_dict() for r in s.scalars(select(PartnerRow))]

    # --- Opportunities ------------------------------------------------------

    def record_opportunity(self, opp: Opportunity) -> str:
        with session_scope() as s:
            s.add(
                OpportunityRow(
                    id=opp.id,
                    kind=opp.kind,
                    title=opp.title,
                    fit_score=opp.fit_score,
                    why=opp.why,
                    suggested_action=opp.suggested_action,
                )
            )
        return opp.id

    def list_opportunities(self) -> list[dict]:
        with session_scope() as s:
            return [r.as_dict() for r in s.scalars(select(OpportunityRow))]

    # --- Performance signals ------------------------------------------------

    def record_signal(self, candidate_id: str, platform: str, metric: str, value: float,
                      themes: list[str] | None = None) -> None:
        with session_scope() as s:
            s.add(
                PerfSignalRow(
                    id=uuid.uuid4().hex,
                    candidate_id=candidate_id,
                    platform=platform,
                    metric=metric,
                    value=value,
                    themes=themes or [],
                )
            )

    # ======================================================================
    # Remix, Parody & Trend Intelligence department
    # ======================================================================

    # --- Scanner sources ---------------------------------------------------

    def add_scanner_source(self, source: dict) -> str:
        row_id = source.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                ScannerSourceRow(
                    id=row_id,
                    name=source.get("name", ""),
                    type=source.get("type", source.get("kind", "rss")),
                    url=source.get("url", ""),
                    topic_area=source.get("topic_area", source.get("category", "")),
                    platform=source.get("platform", ""),
                    scan_frequency=source.get("scan_frequency", "daily"),
                    enabled=source.get("enabled", True),
                    notes=source.get("notes", ""),
                )
            )
        return row_id

    def list_scanner_sources(self, enabled: bool | None = None) -> list[dict]:
        with session_scope() as s:
            stmt = select(ScannerSourceRow)
            if enabled is not None:
                stmt = stmt.where(ScannerSourceRow.enabled == enabled)
            return [r.as_dict() for r in s.scalars(stmt)]

    # --- Scanned items (the reference inbox) -------------------------------

    def add_scanned_item(self, item: dict) -> str:
        row_id = item.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                ScannedItemRow(
                    id=row_id,
                    source_id=item.get("source_id", ""),
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    creator=item.get("creator", ""),
                    platform=item.get("platform", ""),
                    summary=item.get("summary", ""),
                    transcript=item.get("transcript", ""),
                    topic_tags=item.get("topic_tags", []),
                    trend_score=item.get("trend_score", item.get("score", 0.0)),
                    humour_score=item.get("humour_score", 0.0),
                    construction_score=item.get("construction_score", 0.0),
                    invisible_illness_score=item.get("invisible_illness_score", 0.0),
                    sponsor_score=item.get("sponsor_score", 0.0),
                    risk_score=item.get("risk_score", 0.0),
                    rights_status=item.get("rights_status", "reference_only"),
                    status=item.get("status", "new"),
                )
            )
        return row_id

    def list_scanned_items(self, status: str | None = None, limit: int = 100) -> list[dict]:
        with session_scope() as s:
            stmt = select(ScannedItemRow)
            if status:
                stmt = stmt.where(ScannedItemRow.status == status)
            stmt = stmt.order_by(ScannedItemRow.date_found.desc()).limit(limit)
            return [r.as_dict() for r in s.scalars(stmt)]

    # --- Media assets (rights manager) -------------------------------------

    def add_rights_asset(self, asset: dict) -> str:
        row_id = asset.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                RightsAssetRow(
                    id=row_id,
                    file_path=asset.get("file_path", ""),
                    source_url=asset.get("source_url", asset.get("uri", "")),
                    title=asset.get("title", ""),
                    asset_type=asset.get("asset_type", "video"),
                    owner=asset.get("owner", ""),
                    rights_status=asset.get("rights_status", "owned"),
                    licence_notes=asset.get("licence_notes", asset.get("license_note", "")),
                    consent_id=asset.get("consent_id", ""),
                    expiry_date=asset.get("expiry_date"),
                    allowed_platforms=asset.get("allowed_platforms", []),
                    allowed_uses=asset.get("allowed_uses", []),
                    blocked_uses=asset.get("blocked_uses", []),
                )
            )
        return row_id

    def list_rights_assets(self, rights_status: str | None = None) -> list[dict]:
        with session_scope() as s:
            stmt = select(RightsAssetRow)
            if rights_status:
                stmt = stmt.where(RightsAssetRow.rights_status == rights_status)
            return [r.as_dict() for r in s.scalars(stmt)]

    def get_rights_asset(self, asset_id: str) -> dict | None:
        with session_scope() as s:
            row = s.get(RightsAssetRow, asset_id)
            return row.as_dict() if row else None

    def set_asset_rights(self, asset_id: str, rights_status: str,
                         licence_notes: str | None = None) -> dict | None:
        with session_scope() as s:
            row = s.get(RightsAssetRow, asset_id)
            if row is None:
                return None
            row.rights_status = rights_status
            if licence_notes is not None:
                row.licence_notes = licence_notes
            return row.as_dict()

    # --- Pop-culture index -------------------------------------------------

    def add_pop_culture(self, ref: dict) -> str:
        row_id = ref.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                PopCultureRow(
                    id=row_id,
                    title=ref.get("title", ref.get("source_title", "")),
                    source_type=ref.get("source_type", ref.get("reference_type", "film")),
                    reference_description=ref.get("reference_description", ""),
                    exact_quote=ref.get("exact_quote", ""),
                    paraphrase_safe_version=ref.get(
                        "paraphrase_safe_version", ref.get("paraphrase_safe", "")
                    ),
                    tone=ref.get("tone", ""),
                    humour_style=ref.get("humour_style", ""),
                    copyright_risk=ref.get("copyright_risk", "medium"),
                    use_allowed=ref.get("use_allowed", True),
                    suggested_invisable_angle=ref.get(
                        "suggested_invisable_angle", ref.get("content_angle", "")
                    ),
                    platforms=ref.get("platforms", []),
                    related_topics=ref.get("related_topics", []),
                )
            )
        return row_id

    def list_pop_culture(self, limit: int = 200) -> list[dict]:
        with session_scope() as s:
            return [r.as_dict() for r in s.scalars(select(PopCultureRow).limit(limit))]

    def add_meme_format(self, fmt: dict) -> str:
        row_id = fmt.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                MemeFormatRow(
                    id=row_id,
                    format_name=fmt.get("format_name", fmt.get("name", "")),
                    description=fmt.get("description", ""),
                    structure=fmt.get("structure", ""),
                    example_safe_version=fmt.get(
                        "example_safe_version", fmt.get("example_angle", "")
                    ),
                    platform=fmt.get("platform", ""),
                    humour_style=fmt.get("humour_style", ""),
                    risk_score=fmt.get("risk_score", 0.0),
                    related_topics=fmt.get("related_topics", []),
                )
            )
        return row_id

    def list_meme_formats(self, limit: int = 200) -> list[dict]:
        with session_scope() as s:
            return [r.as_dict() for r in s.scalars(select(MemeFormatRow).limit(limit))]

    # --- Remix jobs --------------------------------------------------------

    def add_remix_job(self, job: dict) -> str:
        row_id = job.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                RemixJobRow(
                    id=row_id,
                    input_topic=job.get("input_topic", job.get("topic", "")),
                    reference_item_id=job.get("reference_item_id", ""),
                    asset_id=job.get("asset_id", ""),
                    output_type=job.get("output_type", "parody"),
                    mode=job.get("mode", "create_parody"),
                    script=job.get("script", ""),
                    voiceover_script=job.get("voiceover_script", ""),
                    caption=job.get("caption", ""),
                    hashtags=job.get("hashtags", []),
                    tags=job.get("tags", []),
                    platform=job.get("platform", ""),
                    rights_check_status=job.get("rights_check_status", "pending"),
                    brand_check_status=job.get("brand_check_status", "pending"),
                    approval_status=job.get("approval_status", "pending_review"),
                    risk_score=job.get("risk_score", 0.0),
                    pack=job.get("pack", {}),
                )
            )
        return row_id

    def list_remix_jobs(self, approval_status: str | None = None, limit: int = 100) -> list[dict]:
        with session_scope() as s:
            stmt = select(RemixJobRow)
            if approval_status:
                stmt = stmt.where(RemixJobRow.approval_status == approval_status)
            stmt = stmt.order_by(RemixJobRow.created_at.desc()).limit(limit)
            return [r.as_dict() for r in s.scalars(stmt)]

    def set_remix_job_status(self, job_id: str, approval_status: str) -> dict | None:
        with session_scope() as s:
            row = s.get(RemixJobRow, job_id)
            if row is None:
                return None
            row.approval_status = approval_status
            return row.as_dict()

    # --- Extracted hooks & subtitles ---------------------------------------

    def add_extracted_hook(self, hook: dict) -> str:
        row_id = hook.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                ExtractedHookRow(
                    id=row_id,
                    scanned_item_id=hook.get("scanned_item_id", hook.get("source_ref", "")),
                    hook_text=hook.get("hook_text", hook.get("text", "")),
                    hook_type=hook.get("hook_type", ""),
                    platform=hook.get("platform", ""),
                    strength_score=hook.get("strength_score", hook.get("strength", 0.0)),
                    adapted_invisable_version=hook.get("adapted_invisable_version", ""),
                )
            )
        return row_id

    def list_extracted_hooks(self, limit: int = 200) -> list[dict]:
        with session_scope() as s:
            return [r.as_dict() for r in s.scalars(select(ExtractedHookRow).limit(limit))]

    def add_subtitle(self, sub: dict) -> str:
        row_id = sub.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                SubtitleRow(
                    id=row_id,
                    asset_id=sub.get("asset_id", ""),
                    transcript=sub.get("transcript", ""),
                    srt_path=sub.get("srt_path", ""),
                    burned_video_path=sub.get("burned_video_path", ""),
                    language=sub.get("language", "en"),
                )
            )
        return row_id

    def list_subtitles(self, asset_id: str | None = None, limit: int = 200) -> list[dict]:
        with session_scope() as s:
            stmt = select(SubtitleRow)
            if asset_id:
                stmt = stmt.where(SubtitleRow.asset_id == asset_id)
            return [r.as_dict() for r in s.scalars(stmt.limit(limit))]

    # --- Channels & posting schedule ---------------------------------------

    def add_channel(self, channel: Channel) -> str:
        with session_scope() as s:
            s.add(
                ChannelRow(
                    id=channel.id,
                    name=channel.name,
                    platform=channel.platform.value,
                    handle=channel.handle,
                    timezone=channel.timezone,
                    active=channel.active,
                )
            )
        return channel.id

    def list_channels(self) -> list[dict]:
        with session_scope() as s:
            return [r.as_dict() for r in s.scalars(select(ChannelRow))]

    def get_channel(self, channel_id: str) -> dict | None:
        with session_scope() as s:
            row = s.get(ChannelRow, channel_id)
            return row.as_dict() if row else None

    def add_slot(self, slot: ScheduleSlot) -> str:
        with session_scope() as s:
            s.add(
                ScheduleSlotRow(
                    id=slot.id,
                    channel_id=slot.channel_id,
                    weekday=slot.weekday,
                    hour=slot.hour,
                    minute=slot.minute,
                    active=slot.active,
                )
            )
        return slot.id

    def list_slots(self, channel_id: str | None = None) -> list[ScheduleSlot]:
        with session_scope() as s:
            stmt = select(ScheduleSlotRow)
            if channel_id:
                stmt = stmt.where(ScheduleSlotRow.channel_id == channel_id)
            return [
                ScheduleSlot(
                    id=r.id,
                    channel_id=r.channel_id,
                    weekday=r.weekday,
                    hour=r.hour,
                    minute=r.minute,
                    active=r.active,
                )
                for r in s.scalars(stmt)
            ]

    def taken_slots(self) -> set[datetime]:
        """The scheduled_at times already assigned (so we never double-book a slot)."""
        with session_scope() as s:
            rows = s.scalars(
                select(QueueItemRow).where(QueueItemRow.scheduled_at.is_not(None))
            )
            return {r.scheduled_at for r in rows if r.scheduled_at}

    def assign_schedule(self, item_id: str, when: datetime) -> dict | None:
        """Pin an item to a specific posting time and mark it scheduled."""
        with session_scope() as s:
            row = s.get(QueueItemRow, item_id)
            if row is None:
                return None
            row.scheduled_at = when
            row.status = QueueStatus.SCHEDULED.value
            return row.as_dict()

    def due_for_publish(self, now: datetime, limit: int = 50) -> list[dict]:
        """Approved items (immediate) + scheduled items whose time has arrived."""
        with session_scope() as s:
            approved = list(
                s.scalars(
                    select(QueueItemRow)
                    .where(QueueItemRow.status == QueueStatus.APPROVED.value)
                    .limit(limit)
                )
            )
            scheduled = [
                r
                for r in s.scalars(
                    select(QueueItemRow).where(QueueItemRow.status == QueueStatus.SCHEDULED.value)
                )
                if r.scheduled_at is not None and _as_utc(r.scheduled_at) <= _as_utc(now)
            ]
            return [r.as_dict() for r in (approved + scheduled)][:limit]

    # --- Media library ------------------------------------------------------

    def add_media_asset(self, queue_item_id: str, kind: str, spec: str, path: str,
                        backend: str, status: str = "rendered") -> str:
        asset_id = uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                MediaAssetRow(
                    id=asset_id,
                    queue_item_id=queue_item_id,
                    kind=kind,
                    spec=spec,
                    path=path,
                    backend=backend,
                    status=status,
                )
            )
        return asset_id

    def list_media(self, queue_item_id: str | None = None) -> list[dict]:
        with session_scope() as s:
            stmt = select(MediaAssetRow)
            if queue_item_id:
                stmt = stmt.where(MediaAssetRow.queue_item_id == queue_item_id)
            return [r.as_dict() for r in s.scalars(stmt)]

    # --- Credible sources & claims -----------------------------------------

    def add_source(self, source: dict) -> str:
        source_id = source.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                SourceRow(
                    id=source_id,
                    name=source.get("name", "Untitled source"),
                    url=source.get("url", ""),
                    source_type=source.get("source_type", "news"),
                    credibility_level=source.get("credibility_level", 3),
                    country=source.get("country", "UK"),
                    topic_area=source.get("topic_area", ""),
                    rss_url=source.get("rss_url", ""),
                    enabled=source.get("enabled", True),
                    notes=source.get("notes", ""),
                )
            )
        return source_id

    def list_sources(self, enabled: bool | None = None) -> list[dict]:
        with session_scope() as s:
            stmt = select(SourceRow)
            if enabled is not None:
                stmt = stmt.where(SourceRow.enabled == enabled)
            stmt = stmt.order_by(SourceRow.credibility_level.asc())
            return [r.as_dict() for r in s.scalars(stmt)]

    def get_source(self, source_id: str) -> dict | None:
        with session_scope() as s:
            row = s.get(SourceRow, source_id)
            return row.as_dict() if row else None

    def set_source_enabled(self, source_id: str, enabled: bool) -> dict | None:
        with session_scope() as s:
            row = s.get(SourceRow, source_id)
            if row is None:
                return None
            row.enabled = enabled
            return row.as_dict()

    def add_source_claim(self, claim: dict) -> str:
        claim_id = claim.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                SourceClaimRow(
                    id=claim_id,
                    source_id=claim.get("source_id", ""),
                    title=claim.get("title", ""),
                    claim_text=claim.get("claim_text", ""),
                    quoted_text=claim.get("quoted_text", ""),
                    paraphrase=claim.get("paraphrase", ""),
                    url=claim.get("url", ""),
                    publication_date=claim.get("publication_date"),
                    confidence_score=claim.get("confidence_score", 0.5),
                    primary_or_secondary=claim.get("primary_or_secondary", "secondary"),
                    fact_checked_status=claim.get("fact_checked_status", "unverified"),
                )
            )
        return claim_id

    def list_source_claims(self, source_id: str | None = None,
                           fact_checked_status: str | None = None,
                           limit: int = 200) -> list[dict]:
        with session_scope() as s:
            stmt = select(SourceClaimRow)
            if source_id:
                stmt = stmt.where(SourceClaimRow.source_id == source_id)
            if fact_checked_status:
                stmt = stmt.where(SourceClaimRow.fact_checked_status == fact_checked_status)
            stmt = stmt.order_by(SourceClaimRow.created_at.desc()).limit(limit)
            return [r.as_dict() for r in s.scalars(stmt)]

    def get_source_claim(self, claim_id: str) -> dict | None:
        with session_scope() as s:
            row = s.get(SourceClaimRow, claim_id)
            return row.as_dict() if row else None

    def set_claim_fact_checked(self, claim_id: str, status: str) -> dict | None:
        with session_scope() as s:
            row = s.get(SourceClaimRow, claim_id)
            if row is None:
                return None
            row.fact_checked_status = status
            return row.as_dict()

    # --- Content War Chest --------------------------------------------------

    def add_war_chest_item(self, item: dict) -> str:
        """Stock an approved asset into the reserve. ``item`` is a plain dict."""
        row_id = item.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                WarChestItemRow(
                    id=row_id,
                    queue_item_id=item.get("queue_item_id", ""),
                    candidate_id=item.get("candidate_id", ""),
                    title=item.get("title", ""),
                    category=item.get("category", "evergreen"),
                    platform=item.get("platform", ""),
                    pillar=item.get("pillar", ""),
                    evergreen=item.get("evergreen", False),
                    reserve_status=item.get("reserve_status", "ready"),
                    quality_score=item.get("quality_score", 0.0),
                    mission_score=item.get("mission_score", 0.0),
                    humour_score=item.get("humour_score", 0.0),
                    risk_score=item.get("risk_score", 0.0),
                    freshness_score=item.get("freshness_score", 1.0),
                    tags=item.get("tags", []),
                    payload=item.get("payload", {}),
                    expiry_date=item.get("expiry_date"),
                    notes=item.get("notes", ""),
                )
            )
        return row_id

    def war_chest_has_queue_item(self, queue_item_id: str) -> bool:
        """Whether a queue item is already stocked (so stocking is idempotent)."""
        with session_scope() as s:
            stmt = select(WarChestItemRow).where(
                WarChestItemRow.queue_item_id == queue_item_id
            )
            return s.scalars(stmt).first() is not None

    def list_war_chest(self, category: str | None = None, reserve_status: str | None = None,
                       limit: int = 500) -> list[dict]:
        with session_scope() as s:
            stmt = select(WarChestItemRow)
            if category:
                stmt = stmt.where(WarChestItemRow.category == category)
            if reserve_status:
                stmt = stmt.where(WarChestItemRow.reserve_status == reserve_status)
            stmt = stmt.order_by(WarChestItemRow.created_at.desc()).limit(limit)
            return [r.as_dict() for r in s.scalars(stmt)]

    def get_war_chest_item(self, item_id: str) -> dict | None:
        with session_scope() as s:
            row = s.get(WarChestItemRow, item_id)
            return row.as_dict() if row else None

    def war_chest_counts(self) -> dict[str, int]:
        """Reserve counts overall, by status, and by category."""
        with session_scope() as s:
            by_status: dict[str, int] = {}
            by_category: dict[str, int] = {}
            ready = 0
            for row in s.scalars(select(WarChestItemRow)):
                by_status[row.reserve_status] = by_status.get(row.reserve_status, 0) + 1
                if row.reserve_status == "ready":
                    ready += 1
                    by_category[row.category] = by_category.get(row.category, 0) + 1
            return {"ready": ready, "by_status": by_status, "by_category": by_category}

    def update_war_chest_item(self, item_id: str, **fields) -> dict | None:
        with session_scope() as s:
            row = s.get(WarChestItemRow, item_id)
            if row is None:
                return None
            for k, v in fields.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            return row.as_dict()

    def mark_war_chest_used(self, item_id: str) -> dict | None:
        """Mark a reserve item as used: stamp last_used_at and bump reuse_count."""
        with session_scope() as s:
            row = s.get(WarChestItemRow, item_id)
            if row is None:
                return None
            row.reserve_status = "used"
            row.last_used_at = _now()
            row.reuse_count = (row.reuse_count or 0) + 1
            return row.as_dict()


def _as_utc(dt: datetime) -> datetime:

    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


_singleton: Repository | None = None


def get_repository() -> Repository:
    global _singleton
    if _singleton is None:
        _singleton = Repository()
    return _singleton
