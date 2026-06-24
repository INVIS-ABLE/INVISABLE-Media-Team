"""API routes — the orchestration surface that makes the engines one platform.

These endpoints are deliberately thin: they wire HTTP to the engines, which hold all
the logic. n8n workflows and the Open WebUI call these to run the daily cycle.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from invisable_os.brain import get_brain
from invisable_os.engines import (
    AlgorithmWatchtower,
    CommunityEngagement,
    IntelligenceHarvester,
)
from invisable_os.engines.tournament import ContentTournamentEngine
from invisable_os.guardrails import NEVER_DO, NEVER_OPTIMISE_FOR, OPTIMISE_FOR, check
from invisable_os.guardrails.policy import PRIME_DIRECTIVE
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform
from invisable_os.models.metrics import PerformanceSignal

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
