"""Platform Compliance Watchdog — keep INVISABLE® accounts alive, trusted, compliant.

This engine protects the accounts from flags, spam signals, shadowban indicators,
suspension risk, copyright strikes, T&C breaches and unsafe automation. It is a pure,
deterministic analyser: it **monitors, warns, pauses and downgrades** — it never
performs or bypasses any platform action.

Core rule, encoded as the engine's whole posture:

    The system must comply with TikTok, Instagram, Facebook and Meta rules. It must
    not bypass CAPTCHAs, bans, rate limits, login checks, security checks, or platform
    protections. The app may draft, suggest, queue and analyse. Stephen approves
    sensitive actions. **If growth conflicts with account safety, account safety wins.**

There is deliberately no code here (or anywhere this calls) that auto-follows,
auto-likes, auto-DMs, spams comments, solves CAPTCHAs, or evades restrictions — the
Watchdog's only powers are to raise findings, lower the posting mode, and recommend
that Stephen step in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"          # safe to continue
    MEDIUM = "medium"    # warn Stephen and require review
    HIGH = "high"        # pause automation and require manual approval
    CRITICAL = "critical"  # stop posting immediately, emergency warning


_RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
_RISK_DEDUCTION = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 8,
    RiskLevel.HIGH: 20,
    RiskLevel.CRITICAL: 40,
}


class PostingMode(StrEnum):
    INTRODUCTION = "introduction"          # 1–3/day, all manual approval
    MODEST_GROWTH = "modest_growth"        # 3–6/day, story pushes, comments drafted
    ACTIVE_INFLUENCER = "active_influencer"  # 6–12/day, trend reactions, strict dupes
    CAREER = "career"                      # 12–20/day, only when health is strong
    MANUAL_ONLY = "manual_only"            # automation off; Stephen posts by hand


@dataclass(frozen=True)
class ModeLimit:
    min_posts: int
    max_posts: int
    manual_approval: bool          # every post needs Stephen's approval
    auto_comments: bool            # the system may post comments itself (never true)
    comments_drafted: bool         # comments may be *drafted* for approval
    auto_reposts: bool
    story_pushes: bool
    trend_reactions: bool
    strict_duplicate_checks: bool
    requires_strong_health: bool

    def as_dict(self) -> dict:
        return {
            "min_posts": self.min_posts,
            "max_posts": self.max_posts,
            "manual_approval": self.manual_approval,
            "auto_comments": self.auto_comments,
            "comments_drafted": self.comments_drafted,
            "auto_reposts": self.auto_reposts,
            "story_pushes": self.story_pushes,
            "trend_reactions": self.trend_reactions,
            "strict_duplicate_checks": self.strict_duplicate_checks,
            "requires_strong_health": self.requires_strong_health,
        }


# auto_comments is False in every mode — the system never auto-posts comments.
# Fields: min, max, manual_approval, auto_comments, comments_drafted, auto_reposts,
#         story_pushes, trend_reactions, strict_duplicate_checks, requires_strong_health
MODE_LIMITS: dict[PostingMode, ModeLimit] = {
    PostingMode.INTRODUCTION: ModeLimit(
        1, 3, True, False, False, False, False, False, True, False
    ),
    PostingMode.MODEST_GROWTH: ModeLimit(
        3, 6, True, False, True, False, True, False, True, False
    ),
    PostingMode.ACTIVE_INFLUENCER: ModeLimit(
        6, 12, False, False, True, True, True, True, True, False
    ),
    PostingMode.CAREER: ModeLimit(
        12, 20, False, False, True, True, True, True, True, True
    ),
    PostingMode.MANUAL_ONLY: ModeLimit(
        0, 0, True, False, False, False, False, False, True, False
    ),
}

# The forced-downgrade ladder when risk rises (the Watchdog can step the mode down).
DOWNGRADE: dict[PostingMode, PostingMode] = {
    PostingMode.CAREER: PostingMode.ACTIVE_INFLUENCER,
    PostingMode.ACTIVE_INFLUENCER: PostingMode.MODEST_GROWTH,
    PostingMode.MODEST_GROWTH: PostingMode.INTRODUCTION,
    PostingMode.INTRODUCTION: PostingMode.MANUAL_ONLY,
    PostingMode.MANUAL_ONLY: PostingMode.MANUAL_ONLY,
}

# Thresholds (deliberately conservative — safety wins).
MAX_TAGS_PER_POST = 10
MAX_COMMENTS_PER_DAY = 30
MAX_STORY_PUSHES_PER_DAY = 12
REACH_COLLAPSE = -0.4       # reach trend at/below this = collapse
ENGAGEMENT_DROP = -0.3      # engagement trend at/below this = notable drop

# Policy-sensitive wording. The first list is the most serious (health-harm advice).
_MEDICAL_RED = [
    "stop taking your medication", "stop your medication", "cure cancer",
    "miracle cure", "guaranteed cure", "cures your", "throw away your meds",
]
_MEDICAL_AMBER = ["cure", "heal completely", "100% natural cure", "detox your"]
_LEGAL_BENEFIT_AMBER = [
    "guaranteed pip", "you will win your tribunal", "guaranteed to win",
    "legal advice", "guaranteed benefit", "claim guaranteed",
]
_SPAMMY = [
    "follow for follow", "f4f", "like for like", "l4l", "buy followers",
    "follow back", "dm to buy", "free followers",
]


@dataclass
class ComplianceFinding:
    monitor: str
    risk: RiskLevel
    detail: str
    recommended_action: str

    def as_dict(self) -> dict:
        return {
            "monitor": self.monitor,
            "risk": self.risk.value,
            "detail": self.detail,
            "recommended_action": self.recommended_action,
        }


@dataclass
class ActivitySnapshot:
    """Everything the Watchdog needs to judge account safety right now."""

    current_mode: PostingMode = PostingMode.INTRODUCTION
    posts_today: int = 0
    comments_today: int = 0
    story_pushes_today: int = 0
    recent_posts: list[dict] = field(default_factory=list)  # queue item dicts
    events: list[dict] = field(default_factory=list)        # compliance events
    reach_trend: float = 0.0        # -1..1 (negative = falling)
    engagement_trend: float = 0.0   # -1..1


@dataclass
class ComplianceReport:
    health_score: int
    risk_level: RiskLevel
    mode: PostingMode
    suggested_mode: PostingMode
    findings: list[ComplianceFinding]
    shadowban_signals: list[str]
    recommended_action: str

    def summary(self) -> dict:
        return {
            "health_score": self.health_score,
            "risk_level": self.risk_level.value,
            "mode": self.mode.value,
            "suggested_mode": self.suggested_mode.value,
            "mode_changed": self.mode != self.suggested_mode,
            "findings": [f.as_dict() for f in self.findings],
            "shadowban_signals": self.shadowban_signals,
            "recommended_action": self.recommended_action,
            "mode_limits": MODE_LIMITS[self.suggested_mode].as_dict(),
            "modes": {m.value: MODE_LIMITS[m].as_dict() for m in PostingMode},
        }


_RECOMMEND = {
    RiskLevel.LOW: "Safe to continue. Keep posting within the current mode's limits.",
    RiskLevel.MEDIUM: "Warn Stephen and require review of the flagged items before they go out.",
    RiskLevel.HIGH: "Pause automation and require manual approval for everything.",
    RiskLevel.CRITICAL: (
        "Stop posting immediately. Switch to Manual Only, check the accounts by hand, "
        "and do not resume until the warnings clear."
    ),
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


class ComplianceWatchdog:
    """Evaluate account safety and decide whether automation may continue."""

    def evaluate(self, snapshot: ActivitySnapshot) -> ComplianceReport:
        findings: list[ComplianceFinding] = []
        findings += self._check_frequency(snapshot)
        findings += self._check_duplicates(snapshot)
        findings += self._check_tagging(snapshot)
        findings += self._check_volume(snapshot)
        findings += self._check_originality(snapshot)
        findings += self._check_wording(snapshot)
        findings += self._check_events(snapshot)

        shadowban_signals = self._shadowban_signals(snapshot)
        if len(shadowban_signals) >= 2:
            findings.append(
                ComplianceFinding(
                    monitor="shadowban_warning",
                    risk=RiskLevel.HIGH,
                    detail=(
                        "Multiple shadowban/flag warning patterns at once: "
                        + "; ".join(shadowban_signals)
                    ),
                    recommended_action=(
                        "Pause high-volume posting, reduce the posting mode, stop "
                        "comments/reposts, suggest safer content, and check the account "
                        "manually. (A shadowban can't be proven — treat as a strong warning.)"
                    ),
                )
            )

        risk_level = self._overall_risk(findings)
        health = self._health_score(findings, snapshot)
        suggested = self._suggest_mode(snapshot.current_mode, risk_level, health)

        return ComplianceReport(
            health_score=health,
            risk_level=risk_level,
            mode=snapshot.current_mode,
            suggested_mode=suggested,
            findings=findings,
            shadowban_signals=shadowban_signals,
            recommended_action=_RECOMMEND[risk_level],
        )

    # --- monitors -----------------------------------------------------------

    def _check_frequency(self, s: ActivitySnapshot) -> list[ComplianceFinding]:
        limit = MODE_LIMITS[s.current_mode].max_posts
        if limit <= 0:
            if s.posts_today > 0:
                return [
                    ComplianceFinding(
                        "posting_frequency",
                        RiskLevel.HIGH,
                        f"{s.posts_today} posts today while in Manual Only mode.",
                        "Stop automated posting; Stephen posts by hand only.",
                    )
                ]
            return []
        if s.posts_today > limit * 1.5:
            return [
                ComplianceFinding(
                    "posting_frequency",
                    RiskLevel.CRITICAL,
                    f"{s.posts_today} posts today — far above the {limit}/day limit for "
                    f"{s.current_mode.value}. This looks like spam to the platform.",
                    "Stop posting now and clear today's remaining queue.",
                )
            ]
        if s.posts_today > limit:
            return [
                ComplianceFinding(
                    "posting_frequency",
                    RiskLevel.HIGH,
                    f"{s.posts_today} posts today — over the {limit}/day limit for "
                    f"{s.current_mode.value}.",
                    "Pause posting for the rest of the day; downgrade the mode.",
                )
            ]
        if s.posts_today >= max(1, limit - 1):
            return [
                ComplianceFinding(
                    "posting_frequency",
                    RiskLevel.MEDIUM,
                    f"{s.posts_today}/{limit} posts today — near the daily limit.",
                    "Hold further posts for review; space them out.",
                )
            ]
        return []

    def _check_duplicates(self, s: ActivitySnapshot) -> list[ComplianceFinding]:
        out: list[ComplianceFinding] = []
        captions: dict[str, int] = {}
        hashtags: dict[str, int] = {}
        media: dict[str, int] = {}
        for item in s.recent_posts:
            cand = item.get("candidate") or {}
            body = _norm(cand.get("body", ""))
            if body:
                captions[body] = captions.get(body, 0) + 1
            tags = cand.get("hashtags") or []
            if tags:
                key = " ".join(sorted(_norm(t) for t in tags))
                hashtags[key] = hashtags.get(key, 0) + 1
            primary = _norm(cand.get("primary_media", ""))
            if primary:
                media[primary] = media.get(primary, 0) + 1

        def worst(counts: dict[str, int]) -> int:
            return max(counts.values(), default=0)

        if worst(captions) >= 2:
            risk = RiskLevel.HIGH if worst(captions) >= 3 else RiskLevel.MEDIUM
            out.append(
                ComplianceFinding(
                    "repeated_captions", risk,
                    f"The same caption appears {worst(captions)}× across recent posts.",
                    "Rewrite duplicates before posting — identical captions trip spam filters.",
                )
            )
        if worst(hashtags) >= 3:
            out.append(
                ComplianceFinding(
                    "repeated_hashtags", RiskLevel.MEDIUM,
                    f"The same hashtag set is reused {worst(hashtags)}× recently.",
                    "Vary hashtags per post; avoid copy-pasted hashtag blocks.",
                )
            )
        if worst(media) >= 2:
            out.append(
                ComplianceFinding(
                    "repeated_media", RiskLevel.HIGH,
                    f"The same media file is reused {worst(media)}× — duplicate uploads "
                    "are a strong spam signal.",
                    "Use distinct media per post, or space reuse far apart.",
                )
            )
        return out

    def _check_tagging(self, s: ActivitySnapshot) -> list[ComplianceFinding]:
        for item in s.recent_posts:
            tags = item.get("tags") or []
            if len(tags) > MAX_TAGS_PER_POST:
                return [
                    ComplianceFinding(
                        "excessive_tagging", RiskLevel.MEDIUM,
                        f"A post tags {len(tags)} accounts (limit {MAX_TAGS_PER_POST}).",
                        "Reduce tags; mass-tagging looks like spam and annoys people.",
                    )
                ]
        return []

    def _check_volume(self, s: ActivitySnapshot) -> list[ComplianceFinding]:
        out: list[ComplianceFinding] = []
        if s.comments_today > MAX_COMMENTS_PER_DAY:
            out.append(
                ComplianceFinding(
                    "excessive_comments", RiskLevel.HIGH,
                    f"{s.comments_today} comments today (limit {MAX_COMMENTS_PER_DAY}).",
                    "Stop commenting; high comment volume is a classic spam/ban signal.",
                )
            )
        if s.story_pushes_today > MAX_STORY_PUSHES_PER_DAY:
            out.append(
                ComplianceFinding(
                    "excessive_story_pushes", RiskLevel.MEDIUM,
                    f"{s.story_pushes_today} story pushes today "
                    f"(limit {MAX_STORY_PUSHES_PER_DAY}).",
                    "Slow down story pushes to a human cadence.",
                )
            )
        return out

    def _check_originality(self, s: ActivitySnapshot) -> list[ComplianceFinding]:
        out: list[ComplianceFinding] = []
        for item in s.recent_posts:
            cand = item.get("candidate") or {}
            title = cand.get("brief") or item.get("id", "a post")
            if cand.get("original") is False:
                out.append(
                    ComplianceFinding(
                        "copyright_risk", RiskLevel.HIGH,
                        f"'{title}' is marked non-original — copyright/strike risk.",
                        "Do not repost others' work as-is. Transform it or get permission.",
                    )
                )
            elif cand.get("source_inspiration"):
                out.append(
                    ComplianceFinding(
                        "reposting_risk", RiskLevel.MEDIUM,
                        f"'{title}' is built on external content "
                        f"({cand.get('source_inspiration')}).",
                        "Confirm it's a genuine transformation, not a re-upload, and "
                        "that any music/audio is cleared for use.",
                    )
                )
        return out

    def _check_wording(self, s: ActivitySnapshot) -> list[ComplianceFinding]:
        out: list[ComplianceFinding] = []
        for item in s.recent_posts:
            cand = item.get("candidate") or {}
            text = _norm(
                " ".join(
                    str(cand.get(k, "")) for k in ("hook", "body", "call_to_action")
                )
            )
            if not text:
                continue
            if any(p in text for p in _MEDICAL_RED):
                out.append(
                    ComplianceFinding(
                        "medical_misinformation", RiskLevel.CRITICAL,
                        "A post contains health-harm wording (e.g. telling people to stop "
                        "medication or claiming a cure).",
                        "Do not post. This risks real harm and a platform takedown.",
                    )
                )
            elif any(p in text for p in _MEDICAL_AMBER):
                out.append(
                    ComplianceFinding(
                        "medical_misinformation", RiskLevel.MEDIUM,
                        "A post uses medical-claim wording ('cure', 'detox') that can be "
                        "read as misinformation.",
                        "Soften to lived-experience framing; avoid medical claims.",
                    )
                )
            if any(p in text for p in _LEGAL_BENEFIT_AMBER):
                out.append(
                    ComplianceFinding(
                        "benefit_legal_risk", RiskLevel.MEDIUM,
                        "A post gives benefit/legal guarantees ('guaranteed PIP', 'legal "
                        "advice').",
                        "Reframe as general info, not advice; never guarantee outcomes.",
                    )
                )
            if any(p in text for p in _SPAMMY):
                out.append(
                    ComplianceFinding(
                        "policy_sensitive_wording", RiskLevel.HIGH,
                        "A post contains engagement-bait/spam wording (e.g. 'follow for "
                        "follow', 'buy followers').",
                        "Remove it — this directly violates platform policy.",
                    )
                )
        return out

    def _check_events(self, s: ActivitySnapshot) -> list[ComplianceFinding]:
        out: list[ComplianceFinding] = []
        kinds = [e.get("kind") for e in s.events]
        counts: dict[str, int] = {}
        for k in kinds:
            if k:
                counts[k] = counts.get(k, 0) + 1

        if counts.get("warning"):
            out.append(
                ComplianceFinding(
                    "platform_warning", RiskLevel.HIGH,
                    f"{counts['warning']} platform warning(s) received.",
                    "Stop posting and address the warning before continuing.",
                )
            )
        if counts.get("content_removed") or counts.get("removed_post"):
            out.append(
                ComplianceFinding(
                    "content_removed", RiskLevel.HIGH,
                    "Content was removed by the platform.",
                    "Review what was removed; do not re-post the same content.",
                )
            )
        if counts.get("login_prompt") or counts.get("security_check"):
            out.append(
                ComplianceFinding(
                    "login_security_prompt", RiskLevel.HIGH,
                    "A login/security check is pending.",
                    "Stephen must complete it manually. Never bypass security checks.",
                )
            )
        failed = counts.get("failed_post", 0)
        if failed >= 3:
            out.append(
                ComplianceFinding(
                    "failed_posts", RiskLevel.HIGH,
                    f"{failed} failed uploads — the platform may be throttling the account.",
                    "Pause posting; switch to manual and check the account.",
                )
            )
        elif failed:
            out.append(
                ComplianceFinding(
                    "failed_posts", RiskLevel.MEDIUM,
                    f"{failed} failed upload(s) recently.",
                    "Retry slowly and watch for more failures.",
                )
            )
        api_err = counts.get("api_error", 0)
        if api_err >= 3:
            out.append(
                ComplianceFinding(
                    "api_errors", RiskLevel.MEDIUM,
                    f"{api_err} API errors — possible connection or rate-limit issue.",
                    "Back off automation; do not retry aggressively.",
                )
            )
        if counts.get("comment_blocked"):
            out.append(
                ComplianceFinding(
                    "comment_risk", RiskLevel.MEDIUM,
                    "Comments are being blocked/hidden by the platform.",
                    "Stop commenting; this is a flag indicator.",
                )
            )
        if s.reach_trend <= REACH_COLLAPSE:
            out.append(
                ComplianceFinding(
                    "reach_collapse", RiskLevel.HIGH,
                    f"Reach has collapsed (trend {s.reach_trend:+.0%}) across recent posts.",
                    "Pause high-volume posting; reduce mode; post safer content.",
                )
            )
        if s.engagement_trend <= ENGAGEMENT_DROP:
            out.append(
                ComplianceFinding(
                    "engagement_drop", RiskLevel.MEDIUM,
                    f"Engagement is below baseline (trend {s.engagement_trend:+.0%}).",
                    "Slow down and review content quality before posting more.",
                )
            )
        return out

    def _shadowban_signals(self, s: ActivitySnapshot) -> list[str]:
        signals: list[str] = []
        counts: dict[str, int] = {}
        for e in s.events:
            k = e.get("kind")
            if k:
                counts[k] = counts.get(k, 0) + 1
        if s.reach_trend <= REACH_COLLAPSE:
            signals.append("sudden reach collapse across multiple posts")
        if counts.get("failed_post", 0) >= 2:
            signals.append("repeated failed uploads")
        if counts.get("api_error", 0) >= 2:
            signals.append("repeated API errors")
        if counts.get("warning"):
            signals.append("warning messages from the platform")
        if counts.get("content_removed") or counts.get("removed_post"):
            signals.append("content removed")
        if s.engagement_trend <= ENGAGEMENT_DROP:
            signals.append("engagement dropped below baseline")
        if counts.get("comment_blocked"):
            signals.append("comments not appearing")
        if counts.get("action_blocked"):
            signals.append("account actions blocked")
        return signals

    # --- aggregation --------------------------------------------------------

    def _overall_risk(self, findings: list[ComplianceFinding]) -> RiskLevel:
        level = RiskLevel.LOW
        for f in findings:
            if _RISK_ORDER[f.risk] > _RISK_ORDER[level]:
                level = f.risk
        return level

    def _health_score(self, findings: list[ComplianceFinding], s: ActivitySnapshot) -> int:
        score = 100
        for f in findings:
            score -= _RISK_DEDUCTION[f.risk]
        # Trend penalties on top of any event findings.
        if s.reach_trend < 0:
            score += int(s.reach_trend * 20)  # up to -20
        if s.engagement_trend < 0:
            score += int(s.engagement_trend * 10)  # up to -10
        return max(0, min(100, score))

    def _suggest_mode(
        self, current: PostingMode, risk: RiskLevel, health: int
    ) -> PostingMode:
        """Force a downgrade when risk is high — safety wins over growth."""
        if risk == RiskLevel.CRITICAL:
            return PostingMode.MANUAL_ONLY
        if risk == RiskLevel.HIGH:
            return DOWNGRADE[current]
        # Career mode is only safe with strong health.
        if current == PostingMode.CAREER and health < 70:
            return PostingMode.ACTIVE_INFLUENCER
        return current
