"""Fixed Tag Network.

INVISABLE® only ever tags approved accounts that the founder has added. The network
is *fixed and opt-in*: the platform never tags random accounts, never tags paused
or do-not-tag members, respects per-platform handles, and caps the number of tags
per post. This keeps engagement relationship-driven and professional.
"""

from __future__ import annotations

from dataclasses import dataclass

from invisable_os.models.content import Platform
from invisable_os.models.departments import TagNetworkMember

DEFAULT_MAX_TAGS = 5


@dataclass
class TagSelection:
    handles: list[str]
    placement: str  # "caption" | "first_comment"
    reason: str


class TagNetwork:
    """Selects which approved accounts to tag on a post, by the network rules."""

    def __init__(self, members: list[TagNetworkMember] | None = None) -> None:
        self.members = members or []

    def add(self, member: TagNetworkMember) -> None:
        self.members.append(member)

    def select(
        self,
        platform: Platform,
        *,
        max_tags: int = DEFAULT_MAX_TAGS,
        campaign_category: str | None = None,
        placement: str = "first_comment",
    ) -> TagSelection:
        """Return the handles to tag for ``platform``, respecting every rule."""
        eligible: list[str] = []
        for m in self.members:
            if not m.approved or m.paused or m.do_not_tag:
                continue
            if campaign_category and m.category != campaign_category:
                continue
            handle = self._handle_for(m, platform)
            if handle:
                eligible.append(handle)

        chosen = eligible[:max_tags]
        reason = (
            f"{len(chosen)} approved {campaign_category or 'network'} member(s) for "
            f"{platform.value}; never tags outside the fixed network."
        )
        return TagSelection(handles=chosen, placement=placement, reason=reason)

    @staticmethod
    def _handle_for(member: TagNetworkMember, platform: Platform) -> str | None:
        if platform == Platform.TIKTOK:
            return member.tiktok_handle
        if platform in (Platform.INSTAGRAM, Platform.THREADS):
            return member.instagram_handle
        return member.instagram_handle or member.tiktok_handle
