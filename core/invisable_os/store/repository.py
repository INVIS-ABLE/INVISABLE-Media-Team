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
from invisable_os.store.db import session_scope
from invisable_os.store.models import (
    ExtractedHookRow,
    MediaAssetRow,
    MemeFormatRow,
    OpportunityRow,
    PartnerRow,
    PerfSignalRow,
    PopCultureRow,
    QueueItemRow,
    RemixJobRow,
    ScannedItemRow,
    ScannerSourceRow,
    SubtitleRow,
    TagMemberRow,
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

    def add_media_asset(self, asset: dict) -> str:
        row_id = asset.get("id") or uuid.uuid4().hex
        with session_scope() as s:
            s.add(
                MediaAssetRow(
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

    def list_media_assets(self, rights_status: str | None = None) -> list[dict]:
        with session_scope() as s:
            stmt = select(MediaAssetRow)
            if rights_status:
                stmt = stmt.where(MediaAssetRow.rights_status == rights_status)
            return [r.as_dict() for r in s.scalars(stmt)]

    def get_media_asset(self, asset_id: str) -> dict | None:
        with session_scope() as s:
            row = s.get(MediaAssetRow, asset_id)
            return row.as_dict() if row else None

    def set_asset_rights(self, asset_id: str, rights_status: str,
                         licence_notes: str | None = None) -> dict | None:
        with session_scope() as s:
            row = s.get(MediaAssetRow, asset_id)
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


_singleton: Repository | None = None


def get_repository() -> Repository:
    global _singleton
    if _singleton is None:
        _singleton = Repository()
    return _singleton
