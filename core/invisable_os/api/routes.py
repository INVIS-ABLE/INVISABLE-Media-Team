"""API routes — the orchestration surface that makes the engines one platform.

These endpoints are deliberately thin: they wire HTTP to the engines, which hold all
the logic. n8n workflows and the Open WebUI call these to run the daily cycle.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from invisable_os.agents import AGENT_REGISTRY, TEAM_ORDER, by_team, route
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
from invisable_os.guardrails.model_licensing import MODEL_LICENCES, licence_check
from invisable_os.guardrails.policy import PRIME_DIRECTIVE
from invisable_os.media.probes import probe_video
from invisable_os.media.safe_area import Surface, VisualLayoutAgent, get_template
from invisable_os.media.video_qc import RegionModel, VideoQualityGate, VideoSpec
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform, QueueStatus
from invisable_os.models.departments import Partner, TagNetworkMember
from invisable_os.models.metrics import PerformanceSignal
from invisable_os.models.scheduling import Channel, ScheduleSlot
from invisable_os.scheduling import default_week
from invisable_os.services import (
    CREDIBILITY_HIERARCHY,
    AgentSwarm,
    assemble_post,
    calendar,
    check_post,
    gather_topics,
    produce_media,
    publish_due,
    reserve_health,
    run_and_queue_daily,
    run_swarm_cycle,
    schedule_next,
    seed_default_sources,
    select_next,
    stock_approved,
    swarm_stats,
    sync_metrics,
    sync_post_to_dam,
)
from invisable_os.services.swarm import _SCAN_TOPICS as _SWARM_SEED_TOPICS
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
    """Ingest performance signals, learn, and compute the Founder Recognition Index.

    The raw signals and the resulting Founder Recognition Index are persisted, so
    recognition can be tracked over time (see ``GET /v1/founder/recognition``).
    """
    watchtower = AlgorithmWatchtower()
    report = watchtower.ingest(req.signals)
    repo = get_repository()
    for s in req.signals:
        repo.record_signal(s.candidate_id, s.platform, s.metric.value, s.value, s.themes)
    repo.record_founder_recognition(report.founder_recognition_index, report.totals)
    return {
        "totals": report.totals,
        "founder_recognition_index": report.founder_recognition_index,
        "learnings": report.learnings,
    }


@router.get("/v1/founder/recognition")
def founder_recognition() -> dict:
    """The Founder Recognition Index over time, as ingested by the Watchtower."""
    history = get_repository().list_founder_recognition()
    latest = history[-1]["index_value"] if history else 0.0
    return {"latest": latest, "points": len(history), "history": history}


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


@router.post("/v1/media/assemble/{item_id}")
def media_assemble(item_id: str) -> dict:
    """Stitch a post's rendered visual + voiceover + captions into a final cutdown."""
    return assemble_post(item_id)


@router.get("/v1/media")
def list_media(item_id: str | None = None) -> dict:
    return {"assets": get_repository().list_media(item_id)}


# --- Integrations: ResourceSpace (DAM) + Metricool (metrics) -----------------


class MetricsSyncRequest(BaseModel):
    signals: list[PerformanceSignal] | None = None
    start: str = ""
    end: str = ""


@router.post("/v1/dam/sync/{item_id}")
def dam_sync(item_id: str) -> dict:
    """Push a post's finished assets into ResourceSpace (dry-run unless configured)."""
    return sync_post_to_dam(item_id)


@router.post("/v1/metrics/sync")
def metrics_sync(req: MetricsSyncRequest) -> dict:
    """Ingest performance metrics (from Metricool, or provided) into the Watchtower."""
    return sync_metrics(signals=req.signals, start=req.start, end=req.end)


@router.get("/v1/integrations")
def integrations_status() -> dict:
    """Report which external integrations are configured."""
    import os
    import shutil

    from invisable_os.integrations import MetricoolClient, ResourceSpaceClient

    return {
        "resourcespace": ResourceSpaceClient().configured,
        "metricool": MetricoolClient().configured,
        "postiz": bool(os.getenv("POSTIZ_API_URL") and os.getenv("POSTIZ_API_KEY")),
        "comfyui": bool(os.getenv("COMFYUI_BASE_URL")),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
        "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
        "ffmpeg": shutil.which("ffmpeg") is not None,
    }


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


@router.get("/v1/agents/teams")
def agents_by_team() -> dict:
    """The studio grouped into its seven production-pipeline teams, in order."""
    return {
        "pipeline": [t.value for t in TEAM_ORDER],
        "teams": {
            team.value: [
                {"name": a.name, "department": a.department.value, "role": a.role}
                for a in by_team(team)
            ]
            for team in TEAM_ORDER
        },
    }


# --- Visual layout & video quality gate -------------------------------------


class PlaceCaptionRequest(BaseModel):
    platform: Platform = Platform.TIKTOK
    surface: Surface = Surface.REEL
    height: float = Field(default=0.12, gt=0.0, lt=1.0)
    regions: list[RegionModel] = Field(default_factory=list)


@router.get("/v1/safe-area")
def safe_area(platform: Platform = Platform.TIKTOK, surface: Surface = Surface.REEL) -> dict:
    """The platform/surface safe-area template: UI exclusion zones + title-safe box."""
    template = get_template(platform, surface)
    if template is None:
        return {"error": "no template", "platform": platform.value, "surface": surface.value}
    return {
        "platform": template.platform.value,
        "surface": template.surface.value,
        "aspect": template.aspect.value,
        "title_safe": template.title_safe.as_dict(),
        "exclusions": [
            {"name": z.name, "reason": z.reason, "box": z.box.as_dict()}
            for z in template.exclusions
        ],
    }


@router.post("/v1/layout/place-caption")
def place_caption(req: PlaceCaptionRequest) -> dict:
    """Ask the Visual Layout Agent where a caption can go without blocking anything."""
    template = get_template(req.platform, req.surface)
    if template is None:
        return {"error": "no template", "platform": req.platform.value,
                "surface": req.surface.value}
    placement = VisualLayoutAgent().place_caption(
        template, height=req.height, regions=[r.to_region() for r in req.regions]
    )
    return placement.as_dict()


@router.post("/v1/video/qc")
def video_qc(spec: VideoSpec) -> dict:
    """Run the full pre-approval video quality gate over a structured clip spec."""
    return VideoQualityGate().check(spec).summary()


class ProbeRequest(BaseModel):
    path: str  # server-local path to the rendered clip (e.g. on the GPU box)
    spec: VideoSpec | None = None  # annotations the probes can't infer


@router.post("/v1/video/probe")
def video_probe(req: ProbeRequest) -> dict:
    """Probe a rendered clip (FFmpeg + Whisper) then run the quality gate.

    ``probe_backend`` in the returned spec is ``ffmpeg`` when the real tools ran and
    ``dry-run`` when they aren't installed (the spec passes through unchanged).
    """
    spec = probe_video(req.path, req.spec)
    return {"spec": spec.model_dump(), "report": VideoQualityGate().check(spec).summary()}


# --- Generation-model licensing ---------------------------------------------


class LicenceCheckRequest(BaseModel):
    models: list[str]
    commercial: bool = True


@router.get("/v1/licensing/models")
def list_model_licences() -> dict:
    """The generation/detector models known to the licence gate."""
    return {
        "count": len(MODEL_LICENCES),
        "models": [
            {"name": m.name, "licence": m.licence, "commercial": m.commercial,
             "kind": m.kind, "verify": m.verify, "note": m.note}
            for m in MODEL_LICENCES
        ],
    }


@router.post("/v1/licensing/check")
def check_model_licences(req: LicenceCheckRequest) -> dict:
    """Gate a list of generation/detector models for commercial-use licence."""
    return licence_check(req.models, commercial=req.commercial).model_dump()


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


# --- Credible sources & the fact-check rule ---------------------------------


class SourceRequest(BaseModel):
    name: str
    url: str = ""
    source_type: str = "news"
    credibility_level: int = 3
    country: str = "UK"
    topic_area: str = ""
    rss_url: str = ""
    enabled: bool = True
    notes: str = ""


class SourceClaimRequest(BaseModel):
    source_id: str = ""
    title: str = ""
    claim_text: str = ""
    quoted_text: str = ""
    paraphrase: str = ""
    url: str = ""
    publication_date: str | None = None
    confidence_score: float = 0.5
    primary_or_secondary: str = "secondary"
    fact_checked_status: str = "unverified"


class FactCheckRequest(BaseModel):
    text: str
    source_ids: list[str] = Field(default_factory=list)


@router.get("/v1/sources")
def list_sources(enabled: bool | None = None) -> dict:
    """List credible sources, ordered best-credibility-first."""
    return {"sources": get_repository().list_sources(enabled=enabled)}


@router.post("/v1/sources")
def add_source(req: SourceRequest) -> dict:
    return {"id": get_repository().add_source(req.model_dump())}


@router.get("/v1/sources/hierarchy")
def source_hierarchy() -> dict:
    """The preferred source-credibility hierarchy (tier 1 best → 8 lowest)."""
    return {
        "hierarchy": [
            {"source_type": k, "tier": tier, "label": label}
            for k, (tier, label) in sorted(CREDIBILITY_HIERARCHY.items(), key=lambda kv: kv[1][0])
        ]
    }


@router.get("/v1/sources/{source_id}/claims")
def list_source_claims(source_id: str) -> dict:
    return {"claims": get_repository().list_source_claims(source_id=source_id)}


@router.post("/v1/sources/{source_id}/claims")
def add_source_claim(source_id: str, req: SourceClaimRequest) -> dict:
    payload = req.model_dump()
    payload["source_id"] = source_id
    return {"id": get_repository().add_source_claim(payload)}


@router.post("/v1/factcheck")
def factcheck(req: FactCheckRequest) -> dict:
    """Apply the Credible Source Rule: is this fact-led, and is it sourced?"""
    repo = get_repository()
    sources = [s for sid in req.source_ids if (s := repo.get_source(sid))]
    return check_post(req.text, sources).as_dict()


# --- Content War Chest (the reserve) ----------------------------------------


class WarChestSelectRequest(BaseModel):
    platform: str | None = None
    category: str | None = None
    mark_used: bool = True


@router.get("/v1/warchest")
def warchest_health() -> dict:
    """Reserve level, tier, recommended cadence and category spread."""
    return reserve_health()


@router.get("/v1/warchest/items")
def warchest_items(category: str | None = None, reserve_status: str | None = "ready") -> dict:
    """List reserve items, optionally filtered by category / reserve status."""
    items = get_repository().list_war_chest(category=category, reserve_status=reserve_status)
    return {"items": items}


@router.post("/v1/warchest/stock")
def warchest_stock() -> dict:
    """Stock all approved queue items into the War Chest (idempotent)."""
    return stock_approved()


@router.post("/v1/warchest/select")
def warchest_select(req: WarChestSelectRequest) -> dict:
    """Draw the best non-repetitive ready item for the next slot, and mark it used."""
    return select_next(platform=req.platform, category=req.category, mark_used=req.mark_used)


# --- Agent swarm (20-bot content production) --------------------------------


class SwarmRunRequest(BaseModel):
    drafts_per_topic: int = Field(default=2, ge=1, le=20)
    live_sources: bool = Field(default=True, description="Scan live source feeds (else seed pool).")


@router.get("/v1/swarm/bots")
def swarm_bots() -> dict:
    """The 20 specialist bots with their lifetime contribution totals."""
    return {"bots": AgentSwarm().bots()}


@router.get("/v1/swarm/stats")
def swarm_statistics() -> dict:
    """Production funnel + per-bot pass rates + reserve health, for the dashboard."""
    return swarm_stats()


@router.post("/v1/swarm/run")
def swarm_run(req: SwarmRunRequest) -> dict:
    """Run one swarm cycle: scan → generate → gate → stock. Reject-heavy by design."""
    return run_swarm_cycle(drafts_per_topic=req.drafts_per_topic, live_sources=req.live_sources)


@router.get("/v1/swarm/outputs")
def swarm_outputs(cycle_id: str | None = None, bot_name: str | None = None) -> dict:
    """Recent per-bot output records (optionally filtered by cycle or bot)."""
    return {"outputs": get_repository().list_bot_outputs(cycle_id=cycle_id, bot_name=bot_name)}


@router.get("/v1/swarm/topics")
def swarm_topics(live: bool = True) -> dict:
    """Preview the topics each scanner bot would feed this cycle (live → seed fallback)."""
    topics = gather_topics(_SWARM_SEED_TOPICS, live=live)
    return {"live": live, "topics": topics, "total": sum(len(v) for v in topics.values())}


@router.post("/v1/swarm/sources/seed")
def swarm_seed_sources() -> dict:
    """Seed the starter set of credible UK-first feeds for the scanner bots."""
    return {"added": seed_default_sources()}
