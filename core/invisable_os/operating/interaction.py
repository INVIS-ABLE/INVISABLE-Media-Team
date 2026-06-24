"""The Interaction Centre — where the co-pilot drafts, and Stephen sends.

This is the human-in-the-loop home for everything that needs a reply or a decision:
comments, mentions, story replies, community questions, creator posts worth engaging
with, collaboration opportunities, and urgent messages.

The AI **drafts** replies (always polite, supportive, on-mission, run through the
shared guardrails so they can never carry heart/kiss emoji, engagement-bait or spam).
Stephen **sends** them. Nothing here ever auto-sends, auto-DMs or auto-follows.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from invisable_os.engines.engagement import CommunityEngagement
from invisable_os.models.content import Platform
from invisable_os.store import get_repository

_FLAG_KEY = "interaction_centre"


class InteractionKind(StrEnum):
    COMMENT = "comment"  # a comment on our post needing a reply
    MENTION = "mention"  # we were mentioned/tagged
    STORY_REPLY = "story_reply"  # a reply to one of our stories
    COMMUNITY_QUESTION = "community_question"  # someone asking the community a question
    CREATOR_POST = "creator_post"  # a creator's post worth engaging with
    COLLABORATION = "collaboration"  # a collaboration opportunity
    URGENT_MESSAGE = "urgent_message"  # something needing prompt human attention


class InteractionStatus(StrEnum):
    NEEDS_REPLY = "needs_reply"  # awaiting a drafted reply
    DRAFTED = "drafted"  # AI has drafted a reply; awaiting Stephen
    SENT = "sent"  # Stephen sent it (recorded, not auto-posted)
    DISMISSED = "dismissed"  # Stephen chose to skip it


class InteractionItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    kind: InteractionKind
    platform: Platform = Platform.INSTAGRAM
    author: str = Field(default="", description="Who the interaction is from.")
    summary: str = Field(default="", description="The incoming comment/message/post.")
    context: str = Field(default="", description="What it relates to (our post, story…).")
    suggested_reply: str = Field(default="", description="AI draft — Stephen sends it.")
    reply_approved: bool = Field(
        default=False, description="Whether the draft passed the guardrails."
    )
    status: InteractionStatus = InteractionStatus.NEEDS_REPLY
    priority: str = Field(default="normal", description="normal | high | urgent")
    created_at: str = ""


class InteractionCentre:
    """Stores interaction items and drafts compliant replies. Fully offline."""

    def __init__(self) -> None:
        self.engagement = CommunityEngagement()

    # -- storage (repo flag → {"items": [...]}) ------------------------------

    def _load(self) -> list[InteractionItem]:
        data = get_repository().get_flag(_FLAG_KEY, {"items": []})
        return [InteractionItem.model_validate(i) for i in data.get("items", [])]

    def _save(self, items: list[InteractionItem]) -> None:
        get_repository().set_flag(
            _FLAG_KEY, {"items": [i.model_dump(mode="json") for i in items]}
        )

    # -- read ----------------------------------------------------------------

    def list_items(
        self, status: str | None = None, kind: str | None = None
    ) -> list[InteractionItem]:
        items = self._load()
        if status:
            items = [i for i in items if i.status == status]
        if kind:
            items = [i for i in items if i.kind == kind]
        order = {"urgent": 0, "high": 1, "normal": 2}
        items.sort(key=lambda i: (order.get(i.priority, 2), i.created_at))
        return items

    def get(self, item_id: str) -> InteractionItem | None:
        return next((i for i in self._load() if i.id == item_id), None)

    def counts(self) -> dict:
        items = self._load()
        by_status: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for i in items:
            by_status[i.status] = by_status.get(i.status, 0) + 1
            by_kind[i.kind] = by_kind.get(i.kind, 0) + 1
        return {
            "total": len(items),
            "needs_attention": sum(
                1 for i in items
                if i.status in (InteractionStatus.NEEDS_REPLY, InteractionStatus.DRAFTED)
            ),
            "by_status": by_status,
            "by_kind": by_kind,
        }

    # -- write ---------------------------------------------------------------

    def add(self, item: InteractionItem) -> InteractionItem:
        if not item.created_at:
            item.created_at = datetime.now(UTC).isoformat(timespec="seconds")
        items = self._load()
        items.append(item)
        self._save(items)
        return item

    def _update(self, item_id: str, mutate) -> InteractionItem | None:
        items = self._load()
        for idx, i in enumerate(items):
            if i.id == item_id:
                mutate(i)
                items[idx] = i
                self._save(items)
                return i
        return None

    def draft_reply(self, item_id: str) -> InteractionItem | None:
        """Have the AI draft a polite, compliant reply for Stephen to review."""
        item = self.get(item_id)
        if item is None:
            return None
        draft = self.engagement.draft_comment(
            item.summary or item.context, platform=item.platform, creator=item.author or None
        )

        def mutate(i: InteractionItem) -> None:
            i.suggested_reply = draft.text
            i.reply_approved = draft.approved
            i.status = InteractionStatus.DRAFTED

        return self._update(item_id, mutate)

    def edit_reply(self, item_id: str, text: str) -> InteractionItem | None:
        """Stephen edits the drafted reply by hand."""
        def mutate(i: InteractionItem) -> None:
            i.suggested_reply = text
            i.status = InteractionStatus.DRAFTED

        return self._update(item_id, mutate)

    def mark_sent(self, item_id: str) -> InteractionItem | None:
        """Record that Stephen sent the reply. The app never sends it for him."""
        return self._update(item_id, lambda i: setattr(i, "status", InteractionStatus.SENT))

    def dismiss(self, item_id: str) -> InteractionItem | None:
        return self._update(item_id, lambda i: setattr(i, "status", InteractionStatus.DISMISSED))

    def clear(self) -> int:
        n = len(self._load())
        self._save([])
        return n

    # -- demo seeding (expo) -------------------------------------------------

    def seed_demo(self) -> list[InteractionItem]:
        """Populate a realistic, compliant set of interactions for a demo."""
        samples = [
            InteractionItem(
                kind=InteractionKind.COMMENT, platform=Platform.INSTAGRAM,
                author="@chronic_clare", priority="high",
                summary="“But you don’t look ill” — I hear this every day. Thank you for this.",
                context="Comment on our myth-vs-reality reel",
            ),
            InteractionItem(
                kind=InteractionKind.COMMUNITY_QUESTION, platform=Platform.INSTAGRAM,
                author="@newly_diagnosed", priority="urgent",
                summary="Just diagnosed and feeling lost. How do you explain this to your boss?",
                context="Question under our explainer carousel",
            ),
            InteractionItem(
                kind=InteractionKind.CREATOR_POST, platform=Platform.TIKTOK,
                author="@spoonie_sam",
                summary="A creator shared an honest day-in-the-life with chronic fatigue.",
                context="Worth a supportive comment from INVISABLE",
            ),
            InteractionItem(
                kind=InteractionKind.COLLABORATION, platform=Platform.INSTAGRAM,
                author="@trades_wellbeing", priority="high",
                summary="A trades wellbeing group asking if INVISABLE would co-create a post.",
                context="Collaboration opportunity — trades/community fit",
            ),
            InteractionItem(
                kind=InteractionKind.MENTION, platform=Platform.INSTAGRAM,
                author="@bald_builders",
                summary="Tagged INVISABLE in a post about site safety and hidden conditions.",
                context="Mention — partner-adjacent",
            ),
            InteractionItem(
                kind=InteractionKind.STORY_REPLY, platform=Platform.INSTAGRAM,
                author="@quiet_grafter",
                summary="Replied to our story: “Needed this today, cheers Stephen.”",
                context="Reply to today’s founder story",
            ),
        ]
        for s in samples:
            self.add(s)
        return samples


_singleton: InteractionCentre | None = None


def get_interaction_centre() -> InteractionCentre:
    global _singleton
    if _singleton is None:
        _singleton = InteractionCentre()
    return _singleton
