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
    OpportunityRow,
    PartnerRow,
    PerfSignalRow,
    QueueItemRow,
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


_singleton: Repository | None = None


def get_repository() -> Repository:
    global _singleton
    if _singleton is None:
        _singleton = Repository()
    return _singleton
