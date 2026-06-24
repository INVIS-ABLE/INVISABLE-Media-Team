"""Posting & interaction intensity levels — the human-led operating modes.

INVISABLE Media Studio is a **human-led media co-pilot**, not an autonomous posting
bot. Stephen is editor-in-chief, founder voice, and final authority; the AI supports
him (ideas, drafts, captions, suggested comments, media, trend analysis, queue
organisation) but never acts on the world by itself.

These four modes scale *intensity* — how much the co-pilot prepares and how loud the
rhythm is — without ever scaling *autonomy*. The hard human rules below hold at every
level: no auto-DMs, no auto-follows, no auto-comments, no auto-reposts, and human
approval is always required before anything is published or sent.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class OperatingMode(StrEnum):
    """The four posting/interaction intensity levels."""

    INTRODUCTION = "introduction"  # Level 1 — soft launch, safe warm-up
    MODEST_GROWTH = "modest_growth"  # Level 2 — consistent growth, never spammy
    ACTIVE_INFLUENCER = "active_influencer"  # Level 3 — stronger visibility
    CAREER = "career"  # Level 4 — maximum sustainable, still human-led


class ModePolicy(BaseModel):
    """Everything the app needs to behave correctly in one mode.

    The autonomy fields (``auto_*``) are not configurable per level on purpose — they
    are fixed to the safe value so that *no* mode can ever auto-act. They live here so
    the UI can show, at every level, that the human stays in control.
    """

    level: int
    key: OperatingMode
    name: str
    purpose: str

    # Intensity — these DO scale with the level.
    posts_min: int
    posts_max: int
    stories_min: int = 0
    stories_max: int = 0

    # AI support capabilities — what the co-pilot *prepares* (never sends).
    reply_suggestions: bool = False  # draft replies for Stephen to send
    suggest_reposts: bool = False  # propose reposts/remixes (suggest only)
    recommend_trend_reactions: bool = False
    creator_collab_suggestions: bool = False
    recycle_underperformers: bool = False  # turn weak posts into stories
    creator_amplification: bool = False
    aggressive_format_testing: bool = False

    # Posting intensity risk (content risk is always gated separately by guardrails).
    risk_level: str = "low"

    best_for: list[str] = Field(default_factory=list)
    behaviours: list[str] = Field(default_factory=list)

    # --- the hard human rules: identical and immutable across every mode ----

    @property
    def approval_required(self) -> bool:
        """Human approval is ALWAYS required before publishing or interacting."""
        return True

    @property
    def auto_comments(self) -> bool:
        return False

    @property
    def auto_dms(self) -> bool:
        return False

    @property
    def auto_follow(self) -> bool:
        return False

    @property
    def auto_reposts(self) -> bool:
        return False

    @property
    def reply_mode(self) -> str:
        """Replies are only ever drafted — Stephen sends them."""
        return "draft_only"

    def allowances(self) -> dict:
        """Posts/stories this mode allows in a day (a rhythm, not a quota to fill)."""
        return {
            "posts": {"min": self.posts_min, "max": self.posts_max},
            "stories": {"min": self.stories_min, "max": self.stories_max},
        }

    def summary(self) -> dict:
        return {
            "level": self.level,
            "key": self.key.value,
            "name": self.name,
            "purpose": self.purpose,
            "allowances": self.allowances(),
            "risk_level": self.risk_level,
            "approval_required": self.approval_required,
            "human_rules": {
                "auto_comments": self.auto_comments,
                "auto_dms": self.auto_dms,
                "auto_follow": self.auto_follow,
                "auto_reposts": self.auto_reposts,
                "reply_mode": self.reply_mode,
            },
            "capabilities": {
                "reply_suggestions": self.reply_suggestions,
                "suggest_reposts": self.suggest_reposts,
                "recommend_trend_reactions": self.recommend_trend_reactions,
                "creator_collab_suggestions": self.creator_collab_suggestions,
                "recycle_underperformers": self.recycle_underperformers,
                "creator_amplification": self.creator_amplification,
                "aggressive_format_testing": self.aggressive_format_testing,
            },
            "best_for": self.best_for,
            "behaviours": self.behaviours,
        }


MODE_POLICIES: dict[OperatingMode, ModePolicy] = {
    OperatingMode.INTRODUCTION: ModePolicy(
        level=1,
        key=OperatingMode.INTRODUCTION,
        name="Introduction Mode",
        purpose="Soft launch, safe warm-up, low risk.",
        posts_min=1,
        posts_max=3,
        stories_min=0,
        stories_max=0,
        risk_level="low",
        best_for=["First week", "Expo demo", "New accounts", "Testing content quality"],
        behaviours=[
            "1–3 posts per day",
            "No auto-comments, auto-DMs or auto-reposts",
            "All content requires manual approval",
            "All replies are drafted only — Stephen sends them",
            "AI focuses on learning the founder voice and audience response",
        ],
    ),
    OperatingMode.MODEST_GROWTH: ModePolicy(
        level=2,
        key=OperatingMode.MODEST_GROWTH,
        name="Modest Growth Mode",
        purpose="Consistent growth without looking spammy.",
        posts_min=3,
        posts_max=6,
        stories_min=2,
        stories_max=5,
        reply_suggestions=True,
        suggest_reposts=True,
        recommend_trend_reactions=True,
        risk_level="low",
        best_for=["Early growth", "Building rhythm", "Learning what lands"],
        behaviours=[
            "3–6 posts per day",
            "2–5 story updates per day",
            "No auto-DMs",
            "Comments drafted for Stephen to send",
            "Reposts/remixes suggested only",
            "AI can recommend trend reactions",
            "All posts require approval",
        ],
    ),
    OperatingMode.ACTIVE_INFLUENCER: ModePolicy(
        level=3,
        key=OperatingMode.ACTIVE_INFLUENCER,
        name="Active Influencer Mode",
        purpose="Push stronger visibility and founder recognition.",
        posts_min=6,
        posts_max=12,
        stories_min=5,
        stories_max=10,
        reply_suggestions=True,
        suggest_reposts=True,
        recommend_trend_reactions=True,
        creator_collab_suggestions=True,
        recycle_underperformers=True,
        risk_level="moderate",
        best_for=[
            "Campaign pushes", "Awareness weeks", "Major announcements", "Founder growth",
        ],
        behaviours=[
            "6–12 posts per day",
            "5–10 story updates per day",
            "Reply suggestions every day",
            "Creator collaboration suggestions",
            "Trend reactions generated quickly",
            "Underperforming posts can be recycled into stories",
            "AI can prepare batches, but Stephen approves publishing",
        ],
    ),
    OperatingMode.CAREER: ModePolicy(
        level=4,
        key=OperatingMode.CAREER,
        name="Career Mode",
        purpose="Maximum sustainable media growth while staying human-led.",
        posts_min=12,
        posts_max=20,
        stories_min=10,
        stories_max=20,
        reply_suggestions=True,
        suggest_reposts=True,
        recommend_trend_reactions=True,
        creator_collab_suggestions=True,
        recycle_underperformers=True,
        creator_amplification=True,
        aggressive_format_testing=True,
        risk_level="elevated",
        best_for=[
            "Full INVISABLE media operation", "Growth campaigns",
            "Public figure building", "Major launches",
        ],
        behaviours=[
            "12–20 posts per day",
            "High story activity",
            "Daily trend reactions",
            "Daily founder-led, humour, awareness and community content",
            "Daily creator amplification suggestions",
            "AI drafts comments and responses, but Stephen approves them",
            "System aggressively tests content formats",
            "Human approval remains required for publishing and interaction",
        ],
    ),
}

DEFAULT_MODE = OperatingMode.INTRODUCTION


def get_policy(mode: OperatingMode | str) -> ModePolicy:
    """Return the policy for a mode (accepts the enum or its string value)."""
    return MODE_POLICIES[OperatingMode(mode)]


# The non-negotiable human rules, surfaced verbatim in the UI so they're always visible.
GLOBAL_HUMAN_RULES: dict[str, list[str]] = {
    "always": [
        "Keep Stephen in control",
        "Show what it is doing",
        "Allow pause / override",
        "Allow manual editing",
        "Allow manual posting",
        "Allow manual interaction",
        "Support organic posts from Stephen",
        "Leave gaps for real human moments",
    ],
    "never": [
        "Auto-DM people",
        "Auto-follow people",
        "Spam comments",
        "Bypass human checks",
        "Post risky content without approval",
        "Chase engagement at the cost of trust",
    ],
}

# Comment style rules — also enforced structurally by the shared guardrails.
COMMENT_STYLE_RULES: dict[str, list[str]] = {
    "must_be": [
        "Polite", "Respectful", "Supportive", "Positive",
        "Impactful", "Relevant", "Non-spammy",
    ],
    "avoid": [
        "Heart emojis", "Kiss emojis", "Flirtatious emojis", "Excessive emojis",
        "Generic “great post” comments", "Engagement bait",
        "Follow requests", "Cold DM pushes",
    ],
}

FINAL_PRINCIPLE = (
    "The app should not replace Stephen — it should multiply Stephen: more visible, "
    "more consistent, more recognisable and more impactful, while keeping the account "
    "human, trusted and mission-led."
)
