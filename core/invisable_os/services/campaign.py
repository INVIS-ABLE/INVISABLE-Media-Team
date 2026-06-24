"""The Big Campaign Button — mobilise the whole platform behind one theme.

When the founder hits the button, the platform stops scattering and *concentrates*:
it generates a coordinated burst of on-theme content across every content pillar,
gates it through the same hard checks the rest of the platform uses, and surfaces
the matching War Chest reserve as ready reinforcements — so a launch, an awareness
day, or a moment in the news can go out as one deliberate push.

It is deterministic and offline: the generator degrades to templates, the gates are
the real hard-gate code, and crisis review runs first so a sensitive campaign is
treated with care rather than hype.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from invisable_os.engines.generator import Generator
from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.quality import QualityEngine
from invisable_os.guardrails import check as brand_check
from invisable_os.guardrails.crisis import crisis_review
from invisable_os.models.content import ContentCandidate, Platform, QueueStatus
from invisable_os.services.fact_check import check_post
from invisable_os.store import Repository, get_repository

# A coordinated spread across the content pillars — one campaign speaks in many
# voices at once. Each entry is (generator angle, content pillar).
CAMPAIGN_ANGLES: list[tuple[str, str]] = [
    ("founder_voice", "founder"),
    ("explainer", "education"),
    ("solidarity", "community"),
    ("gentle_humour", "humour"),
    ("practical_tip", "partner"),
    ("myth_vs_reality", "trends"),
]

_DEFAULT_POSTS = 12
_MAX_POSTS = 60
_REINFORCE_LIMIT = 12
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with", "your",
    "you", "our", "we", "is", "are", "it", "this", "that", "about", "campaign",
}


@dataclass
class CampaignPlan:
    """The package the Big Campaign Button produces for one theme."""

    campaign_id: str
    theme: str
    brief: str
    platform: str
    requested: int
    crisis: dict = field(default_factory=dict)
    generated: list[dict] = field(default_factory=list)
    reinforcements: list[dict] = field(default_factory=list)
    funnel: dict = field(default_factory=dict)
    persisted: bool = False
    queued_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "theme": self.theme,
            "brief": self.brief,
            "platform": self.platform,
            "requested": self.requested,
            "crisis": self.crisis,
            "funnel": self.funnel,
            "generated": self.generated,
            "reinforcements": self.reinforcements,
            "reinforcement_count": len(self.reinforcements),
            "ready_to_queue": self.funnel.get("usable", 0),
            "persisted": self.persisted,
            "queued_ids": self.queued_ids,
        }


def _tokens(text: str) -> set[str]:
    return {w for w in "".join(c.lower() if c.isalnum() else " " for c in text).split()
            if len(w) > 2 and w not in _STOPWORDS}


def _matches_theme(item: dict, wanted: set[str]) -> bool:
    """A reserve item reinforces the campaign if it shares a theme word."""
    if not wanted:
        return False
    haystack = " ".join(
        str(item.get(k, "")) for k in ("title", "category", "pillar")
    ) + " " + " ".join(item.get("tags") or [])
    return bool(wanted & _tokens(haystack))


class BigCampaign:
    """Generate, gate, and marshal a coordinated burst behind a single theme."""

    def __init__(self, repository: Repository | None = None) -> None:
        self.repo = repository or get_repository()
        self.generator = Generator()
        self.quality = QualityEngine()
        self.mission = MissionEngine()

    def launch(
        self,
        brief: str,
        *,
        theme: str = "",
        posts: int = _DEFAULT_POSTS,
        platform: Platform = Platform.TIKTOK,
        persist: bool = False,
    ) -> dict:
        posts = max(1, min(posts, _MAX_POSTS))
        theme = (theme or brief).strip()
        plan = CampaignPlan(
            campaign_id=uuid.uuid4().hex,
            theme=theme,
            brief=brief,
            platform=platform.value,
            requested=posts,
        )

        # 1. CARE FIRST — a sensitive campaign is flagged before a word is written.
        plan.crisis = crisis_review(brief).as_dict()

        # 2. GENERATE — a coordinated burst across pillars, round-robin to `posts`.
        drafts = self._generate(brief, platform, posts)

        # 3. GATE — brand guardrails hard-reject; quality/mission/fact-check flag.
        survivors, funnel = self._gate(drafts)
        plan.generated = survivors
        plan.funnel = funnel

        # 4. REINFORCE — surface the matching ready reserve (suggested, not consumed).
        wanted = _tokens(theme)
        ready = self.repo.list_war_chest(reserve_status="ready", limit=1000)
        plan.reinforcements = [i for i in ready if _matches_theme(i, wanted)][:_REINFORCE_LIMIT]

        # 5. OPTIONALLY STAGE — enqueue the usable drafts, tagged with the campaign.
        if persist:
            plan.queued_ids = self._enqueue(survivors, plan.campaign_id)
            plan.persisted = True

        return plan.as_dict()

    # -- internals -----------------------------------------------------------

    def _generate(self, brief: str, platform: Platform, posts: int) -> list[ContentCandidate]:
        drafts: list[ContentCandidate] = []
        i = 0
        while len(drafts) < posts:
            angle, pillar = CAMPAIGN_ANGLES[i % len(CAMPAIGN_ANGLES)]
            cands = self.generator.generate(brief, platform, count=1, angle=angle)
            for c in cands:
                c.themes = [*(c.themes or []), pillar]
            drafts.extend(cands)
            i += 1
        return drafts[:posts]

    def _gate(self, drafts: list[ContentCandidate]) -> tuple[list[dict], dict]:
        survivors: list[dict] = []
        brand_pass = needs_review = 0
        for c in drafts:
            verdict = brand_check(c)
            if not verdict.passed:
                continue  # the only hard rejection
            brand_pass += 1
            q = self.quality.score(c)
            fc = check_post(c.full_text, [])  # no source at draft time
            m = self.mission.advise(c)
            flagged = bool(verdict.needs_human_review) or not fc.ok
            if flagged:
                needs_review += 1
            survivors.append(
                {
                    "candidate": c.model_dump(),
                    "quality_avg": q.average(),
                    "quality_passes": q.passes(),
                    "mission_total": m.total(),
                    "mission_verdict": m.verdict,
                    "fact_ok": fc.ok,
                    "needs_review": flagged,
                    "pillar": (c.themes or ["humour"])[-1],
                    "platform": c.platform.value,
                }
            )
        funnel = {
            "raw": len(drafts),
            "brand_passed": brand_pass,
            "brand_rejected": len(drafts) - brand_pass,
            "usable": len(survivors),
            "needs_review": needs_review,
        }
        return survivors, funnel

    def _enqueue(self, survivors: list[dict], campaign_id: str) -> list[str]:
        ids: list[str] = []
        for s in survivors:
            cand = dict(s["candidate"])
            tags = list(cand.get("tags") or [])
            tag = f"campaign:{campaign_id}"
            if tag not in tags:
                tags.append(tag)
            cand["tags"] = tags
            queue_id = self.repo.enqueue(
                {
                    "candidate_id": cand.get("id", ""),
                    "candidate": cand,
                    "status": QueueStatus.PENDING_REVIEW.value,
                    "pillar": s["pillar"],
                    "platform": s["platform"],
                    "quality_avg": s["quality_avg"],
                    "quality_passes": s["quality_passes"],
                    "mission_total": s["mission_total"],
                    "mission_verdict": s["mission_verdict"],
                    "needs_human_review": s["needs_review"],
                    "tags": tags,
                }
            )
            ids.append(queue_id)
        return ids


def launch_campaign(
    brief: str,
    *,
    theme: str = "",
    posts: int = _DEFAULT_POSTS,
    platform: Platform = Platform.TIKTOK,
    persist: bool = False,
    repository: Repository | None = None,
) -> dict:
    """One-call Big Campaign Button: generate + gate + marshal a themed burst."""
    return BigCampaign(repository=repository).launch(
        brief, theme=theme, posts=posts, platform=platform, persist=persist
    )
