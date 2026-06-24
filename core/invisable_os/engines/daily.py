"""Daily Output System.

Produces the day's 20 posts to the exact editorial brief, tying every department
together. Each slot runs a mini content tournament (generate → gate → score →
improve → select), then the winner is scored for mission impact and quality, and
spun through the Content Flywheel into a family of assets.

The fixed daily breakdown (sums to 20):

    3 invisible-illness education    3 trades/community relatable    3 humour
    3 TikTok/Reel scripts            2 carousels                     2 partner-safe
    2 trend reactions                1 founder/mission               1 comment response
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invisable_os.engines.flywheel import ContentFlywheel, FlywheelOutput
from invisable_os.engines.mission import MissionEngine, MissionScore
from invisable_os.engines.personality import ContentPillar
from invisable_os.engines.quality import QualityEngine, QualityScore
from invisable_os.engines.tournament import ContentTournamentEngine
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform


@dataclass
class DailySlot:
    """One scheduled slot in the day's plan."""

    label: str
    pillar: ContentPillar
    platform: Platform
    content_format: ContentFormat
    brief: str
    angle: str = ""  # generator angle that matches this slot's editorial intent


@dataclass
class PlannedPost:
    slot_label: str
    pillar: str
    candidate: ContentCandidate
    mission: MissionScore
    quality: QualityScore
    flywheel: FlywheelOutput
    needs_improvement: bool
    needs_human_review: bool


@dataclass
class DailyPlan:
    posts: list[PlannedPost] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "total": len(self.posts),
            "by_pillar": self._count("pillar"),
            "needs_improvement": sum(1 for p in self.posts if p.needs_improvement),
            "needs_human_review": sum(1 for p in self.posts if p.needs_human_review),
            "total_assets": sum(len(p.flywheel) for p in self.posts),
            "posts": [
                {
                    "slot": p.slot_label,
                    "pillar": p.pillar,
                    "hook": p.candidate.hook,
                    "mission": p.mission.total(),
                    "mission_verdict": p.mission.verdict,
                    "quality_avg": p.quality.average(),
                    "assets": len(p.flywheel),
                    "founder": p.candidate.founder_centred,
                }
                for p in self.posts
            ],
        }

    def _count(self, attr: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for p in self.posts:
            key = getattr(p, attr)
            out[key] = out.get(key, 0) + 1
        return out


# The canonical daily editorial brief.
DAILY_BRIEF: list[DailySlot] = [
    *[
        DailySlot(
            "invisible_illness_education",
            ContentPillar.EDUCATION,
            Platform.INSTAGRAM,
            ContentFormat.CAROUSEL,
            "Teach one concrete, honest thing about living with invisible illness",
            angle="explainer",
        )
        for _ in range(3)
    ],
    *[
        DailySlot(
            "trades_community_relatable",
            ContentPillar.COMMUNITY,
            Platform.INSTAGRAM,
            ContentFormat.TEXT_POST,
            "A relatable moment for tradespeople living with invisible illness",
            angle="solidarity",
        )
        for _ in range(3)
    ],
    *[
        DailySlot(
            "humour",
            ContentPillar.HUMOUR,
            Platform.TIKTOK,
            ContentFormat.SHORT_VIDEO,
            "Warm, self-deprecating British humour about living with invisible illness",
            angle="gentle_humour",
        )
        for _ in range(3)
    ],
    *[
        DailySlot(
            "short_video_script",
            ContentPillar.TRENDS,
            Platform.TIKTOK,
            ContentFormat.SHORT_VIDEO,
            "A TikTok/Reel script that raises awareness of invisible illness",
            angle="myth_vs_reality",
        )
        for _ in range(3)
    ],
    *[
        DailySlot(
            "carousel",
            ContentPillar.EDUCATION,
            Platform.INSTAGRAM,
            ContentFormat.CAROUSEL,
            "An explainer carousel that myth-busts a misconception about invisible illness",
            angle="reframe",
        )
        for _ in range(2)
    ],
    *[
        DailySlot(
            "partner_safe",
            ContentPillar.PARTNER,
            Platform.INSTAGRAM,
            ContentFormat.TEXT_POST,
            "A partner-safe post that supports the trades community (no overclaiming)",
            angle="practical_tip",
        )
        for _ in range(2)
    ],
    *[
        DailySlot(
            "trend_reaction",
            ContentPillar.TRENDS,
            Platform.TIKTOK,
            ContentFormat.SHORT_VIDEO,
            "A genuine reaction to a current trend, tied back to the mission",
            angle="community_prompt",
        )
        for _ in range(2)
    ],
    DailySlot(
        "founder_mission",
        ContentPillar.FOUNDER,
        Platform.INSTAGRAM,
        ContentFormat.SHORT_VIDEO,
        "The founder's genuine advocacy and why INVISABLE exists",
        angle="founder_voice",
    ),
    DailySlot(
        "comment_response",
        ContentPillar.COMMUNITY,
        Platform.INSTAGRAM,
        ContentFormat.TEXT_POST,
        "A supportive response to a common community question or misconception",
        angle="community_prompt",
    ),
]


class DailyContentDirector:
    """Runs the whole agency for a day and returns a structured plan of 20 posts."""

    def __init__(
        self,
        tournament: ContentTournamentEngine | None = None,
        mission: MissionEngine | None = None,
        quality: QualityEngine | None = None,
        flywheel: ContentFlywheel | None = None,
    ) -> None:
        self.tournament = tournament or ContentTournamentEngine()
        self.mission = mission or MissionEngine()
        self.quality = quality or QualityEngine()
        self.flywheel = flywheel or ContentFlywheel()

    def plan_day(
        self,
        *,
        candidates_per_slot: int = 16,
        prior_published: list[ContentCandidate] | None = None,
    ) -> DailyPlan:
        """Plan the day's 20 posts.

        ``prior_published`` seeds the Founder Engine with content already published
        or queued (e.g. from earlier runs) so founder presence tracks the ~80%
        target across days, not just within a single run.
        """
        plan = DailyPlan()
        published: list[ContentCandidate] = list(prior_published or [])
        for slot in DAILY_BRIEF:
            result = self.tournament.run(
                slot.brief,
                slot.platform,
                count=candidates_per_slot,
                select=1,
                content_format=slot.content_format,
                published=published,
                # The daily brief already controls the founder/pillar mix per slot,
                # so don't let per-slot founder promotion override slot intent.
                rebalance_founder=(slot.pillar == ContentPillar.FOUNDER),
                angle=slot.angle or None,
            )
            if not result.winners:
                continue
            winner = result.winners[0].candidate
            published.append(winner)

            quality = self.quality.score(winner)
            mission = self.mission.advise(winner)
            flywheel = self.flywheel.spin(winner)
            verdict = result.winners[0].guardrail

            plan.posts.append(
                PlannedPost(
                    slot_label=slot.label,
                    pillar=slot.pillar.value,
                    candidate=winner,
                    mission=mission,
                    quality=quality,
                    flywheel=flywheel,
                    needs_improvement=not quality.passes(),
                    needs_human_review=verdict.needs_human_review,
                )
            )
        return plan
