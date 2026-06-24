"""API routes — the orchestration surface that makes the engines one platform.

These endpoints are deliberately thin: they wire HTTP to the engines, which hold all
the logic. n8n workflows and the Open WebUI call these to run the daily cycle.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from invisable_os.agents import AGENT_REGISTRY, route
from invisable_os.brain import get_brain
from invisable_os.engines import (
    AlgorithmWatchtower,
    CommunityEngagement,
    ContentFlywheel,
    DailyContentDirector,
    IntelligenceHarvester,
    MissionEngine,
    QualityEngine,
)
from invisable_os.engines.personality import CONTENT_PERSONALITY_MIX
from invisable_os.engines.tournament import ContentTournamentEngine
from invisable_os.guardrails import NEVER_DO, NEVER_OPTIMISE_FOR, OPTIMISE_FOR, check
from invisable_os.guardrails.policy import PRIME_DIRECTIVE
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform, QueueStatus
from invisable_os.models.departments import Partner, TagNetworkMember
from invisable_os.models.metrics import PerformanceSignal
from invisable_os.models.scheduling import Channel, ScheduleSlot
from invisable_os.scheduling import default_week
from invisable_os.services import (
    calendar,
    produce_media,
    publish_due,
    run_and_queue_daily,
    schedule_next,
)
from invisable_os.store import get_repository

router = APIRouter()


# --- requests ---------------------------------------------------------------


class TournamentRequest(BaseModel):
    brief: str
    platform: Platform = Platform.INSTAGRAM
    count: int = Field(default=24, ge=1, le=500)
    select: int = Field(default=3, ge=1, le=50)
    content_format: ContentFormat = ContentFormat.SHORT_VIDEO


class GuardrailRequest(BaseModel):
    text: str
    content_format: ContentFormat = ContentFormat.TEXT_POST
    original: bool = True


class CommentRequest(BaseModel):
    post_summary: str
    platform: Platform = Platform.INSTAGRAM
    creator: str | None = None


class HarvestRequest(BaseModel):
    topics: list[str] | None = None


class WatchtowerRequest(BaseModel):
    signals: list[PerformanceSignal]


# --- routes -----------------------------------------------------------------


@router.get("/v1/values")
def values() -> dict:
    """The platform's values, served from the single source of truth."""
    return {
        "prime_directive": PRIME_DIRECTIVE,
        "optimise_for": list(OPTIMISE_FOR),
        "never_optimise_for": list(NEVER_OPTIMISE_FOR),
        "never_do": list(NEVER_DO),
    }


@router.post("/v1/tournament/run")
def run_tournament(req: TournamentRequest) -> dict:
    """Generate a field, gate + score + improve + rank, and return the winners."""
    engine = ContentTournamentEngine()
    result = engine.run(
        req.brief,
        req.platform,
        count=req.count,
        select=req.select,
        content_format=req.content_format,
    )
    return result.summary()


@router.post("/v1/guardrails/check")
def guardrail_check(req: GuardrailRequest) -> dict:
    """Run the hard-gate guardrails against arbitrary text."""
    candidate = ContentCandidate(
        brief="ad-hoc check",
        platform=Platform.BLOG,
        content_format=req.content_format,
        body=req.text,
        original=req.original,
    )
    verdict = check(candidate)
    return verdict.model_dump()


@router.post("/v1/engagement/comment")
def draft_comment(req: CommentRequest) -> dict:
    """Draft a compliant, supportive community comment."""
    engine = CommunityEngagement()
    draft = engine.draft_comment(req.post_summary, platform=req.platform, creator=req.creator)
    return {"text": draft.text, "approved": draft.approved, "verdict": draft.verdict.model_dump()}


@router.post("/v1/harvest")
def harvest(req: HarvestRequest) -> dict:
    """Harvest abstracted public signals into the Brain."""
    harvester = IntelligenceHarvester()
    signals = harvester.harvest(req.topics)
    return {"count": len(signals), "signals": [s.__dict__ for s in signals]}


@router.post("/v1/watchtower/ingest")
def watchtower_ingest(req: WatchtowerRequest) -> dict:
    """Ingest performance signals, learn, and compute the Founder Recognition Index."""
    watchtower = AlgorithmWatchtower()
    report = watchtower.ingest(req.signals)
    return {
        "totals": report.totals,
        "founder_recognition_index": report.founder_recognition_index,
        "learnings": report.learnings,
    }


class DailyRequest(BaseModel):
    candidates_per_slot: int = Field(default=16, ge=4, le=200)
    persist: bool = Field(default=False, description="Write the day into the approval queue.")


class IdeaRequest(BaseModel):
    brief: str
    hook: str = ""
    body: str = ""
    platform: Platform = Platform.INSTAGRAM
    founder_centred: bool = False


@router.post("/v1/daily/plan")
def daily_plan(req: DailyRequest) -> dict:
    """Run the whole agency for a day: 20 posts, each gated, scored, and spun.

    Set ``persist=true`` to write the day into the durable approval queue.
    """
    if req.persist:
        return run_and_queue_daily(candidates_per_slot=req.candidates_per_slot)
    director = DailyContentDirector()
    plan = director.plan_day(candidates_per_slot=req.candidates_per_slot)
    return plan.summary()


# --- Approval queue (the content lifecycle) ---------------------------------


@router.get("/v1/queue")
def list_queue(status: str | None = None) -> dict:
    """List the approval queue, optionally filtered by lifecycle status."""
    repo = get_repository()
    return {"counts": repo.counts_by_status(), "items": repo.list_queue(status=status)}


@router.get("/v1/queue/{item_id}")
def get_queue_item(item_id: str) -> dict:
    item = get_repository().get_queue_item(item_id)
    return item or {"error": "not found", "id": item_id}


@router.post("/v1/queue/{item_id}/{action}")
def queue_action(item_id: str, action: str) -> dict:
    """Move a queue item: approve | reject | schedule | publish | schedule-next.

    ``schedule-next`` assigns the next open posting slot for the item's channel; the
    others are direct status transitions.
    """
    if action == "schedule-next":
        return schedule_next(item_id)
    mapping = {
        "approve": QueueStatus.APPROVED,
        "reject": QueueStatus.REJECTED,
        "schedule": QueueStatus.SCHEDULED,
        "publish": QueueStatus.PUBLISHED,
    }
    target = mapping.get(action)
    if target is None:
        return {
            "error": f"unknown action '{action}'",
            "allowed": [*mapping, "schedule-next"],
        }
    item = get_repository().transition(item_id, target)
    return item or {"error": "not found", "id": item_id}


@router.post("/v1/publish/run")
def publish_run() -> dict:
    """Take due items live (approved now, or scheduled and time-arrived)."""
    return publish_due()


# --- Scheduling: channels, slots, calendar ----------------------------------


@router.get("/v1/channels")
def list_channels() -> dict:
    return {"channels": get_repository().list_channels()}


@router.post("/v1/channels")
def add_channel(channel: Channel, with_default_schedule: bool = True) -> dict:
    repo = get_repository()
    channel_id = repo.add_channel(channel)
    slots = 0
    if with_default_schedule:
        for slot in default_week(channel_id):
            repo.add_slot(slot)
            slots += 1
    return {"id": channel_id, "slots_created": slots}


@router.post("/v1/channels/{channel_id}/slots")
def add_slot(channel_id: str, slot: ScheduleSlot) -> dict:
    slot.channel_id = channel_id
    return {"id": get_repository().add_slot(slot)}


@router.get("/v1/channels/{channel_id}/slots")
def list_slots(channel_id: str) -> dict:
    return {"slots": [s.model_dump() for s in get_repository().list_slots(channel_id)]}


@router.get("/v1/calendar")
def get_calendar() -> dict:
    """Scheduled posts grouped by day, for a calendar view."""
    return {"calendar": calendar()}


# --- Media pipeline ---------------------------------------------------------


@router.post("/v1/media/produce/{item_id}")
def media_produce(item_id: str) -> dict:
    """Render a queued item's flywheel assets into the media library."""
    return produce_media(item_id)


@router.get("/v1/media")
def list_media(item_id: str | None = None) -> dict:
    return {"assets": get_repository().list_media(item_id)}


# --- Relationship: tag network & partners -----------------------------------


@router.get("/v1/tags")
def list_tags() -> dict:
    return {"members": [m.model_dump() for m in get_repository().list_tag_members()]}


@router.post("/v1/tags")
def add_tag(member: TagNetworkMember) -> dict:
    member_id = get_repository().add_tag_member(member)
    return {"id": member_id}


@router.get("/v1/partners")
def list_partners() -> dict:
    return {"partners": get_repository().list_partners()}


@router.post("/v1/partners")
def add_partner(partner: Partner) -> dict:
    return {"id": get_repository().add_partner(partner)}


@router.get("/v1/opportunities")
def list_opportunities() -> dict:
    return {"opportunities": get_repository().list_opportunities()}


@router.post("/v1/opportunities/scan")
def scan_opportunities(req: HarvestRequest) -> dict:
    """Scan for media/speaking/sponsorship opportunities and persist them."""
    repo = get_repository()
    found = IntelligenceHarvester().scan_opportunities(req.topics)
    for opp in found:
        repo.record_opportunity(opp)
    return {"count": len(found), "opportunities": [o.model_dump() for o in found]}


@router.post("/v1/mission/advise")
def mission_advise(req: IdeaRequest) -> dict:
    """Score an idea against the five mission impacts (the Mission Advisor)."""
    candidate = _candidate_from(req)
    return MissionEngine().advise(candidate).model_dump()


@router.post("/v1/quality/score")
def quality_score(req: IdeaRequest) -> dict:
    """Score an idea across the 11 quality dimensions; report if it passes the bar."""
    candidate = _candidate_from(req)
    q = QualityEngine().score(candidate)
    return {**q.model_dump(), "average": q.average(), "passes": q.passes(), "weakest": q.weakest()}


@router.post("/v1/flywheel/spin")
def flywheel_spin(req: IdeaRequest) -> dict:
    """Spin one idea into a family of assets."""
    candidate = _candidate_from(req)
    out = ContentFlywheel().spin(candidate)
    return {
        "seed_hook": out.seed_hook,
        "future_idea": out.future_idea,
        "assets": [a.__dict__ for a in out.assets],
    }


@router.get("/v1/personality/mix")
def personality_mix() -> dict:
    """The content personality mix the brand publishes against."""
    return {pillar.value: share for pillar, share in CONTENT_PERSONALITY_MIX.items()}


@router.get("/v1/agents")
def list_agents() -> dict:
    """The specialist agent library."""
    return {
        "count": len(AGENT_REGISTRY),
        "agents": [
            {"name": a.name, "department": a.department.value, "role": a.role}
            for a in AGENT_REGISTRY
        ],
    }


@router.get("/v1/agents/route")
def route_agents(task: str) -> dict:
    """Route a free-text task to the best-matched specialist agents."""
    return {"task": task, "agents": [a.name for a in route(task)]}


def _candidate_from(req: IdeaRequest) -> ContentCandidate:
    return ContentCandidate(
        brief=req.brief,
        platform=req.platform,
        hook=req.hook,
        body=req.body or req.brief,
        founder_centred=req.founder_centred,
    )


@router.get("/v1/brain/stats")
def brain_stats() -> dict:
    """How much the platform has learned so far."""
    brain = get_brain()
    return {
        "total_memories": brain.count(),
        "winning_patterns": brain.count("winning_pattern"),
        "performance_learnings": brain.count("performance_learning"),
        "trend_signals": brain.count("trend_signal"),
        "cultural_notes": brain.count("cultural_note"),
    }
