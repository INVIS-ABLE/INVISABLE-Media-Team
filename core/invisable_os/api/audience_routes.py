"""Audience Command HTTP surface — personas, voice bank, and the Hook Laboratory.

Thin wiring over the deterministic engines: list the personas/voices, target a piece
of text to its primary persona, and run the Hook Lab (ten scored hooks, best first).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from invisable_os.engines.audience import (
    PERSONAS,
    VOICE_BANK,
    get_persona,
    pick_voice,
    target_persona,
)
from invisable_os.engines.hooks import HOOK_TYPES, SCORE_AXES, HookLab

audience_router = APIRouter(prefix="/v1", tags=["audience"])


class TargetRequest(BaseModel):
    text: str
    platform: str = ""


class HookLabRequest(BaseModel):
    topic: str
    platform: str = "tiktok"
    persona: str = ""


class VoicePickRequest(BaseModel):
    pillar: str = ""
    persona: str | None = None


@audience_router.get("/personas")
def list_personas() -> dict:
    """The eight audience personas every post can target."""
    return {"personas": [p.as_dict() for p in PERSONAS]}


@audience_router.post("/personas/target")
def target(req: TargetRequest) -> dict:
    """Classify a piece of content to its primary audience persona."""
    return target_persona(req.text, platform=req.platform).as_dict()


@audience_router.get("/voices")
def list_voices() -> dict:
    """The nine creator voice modes."""
    return {"voices": [v.as_dict() for v in VOICE_BANK]}


@audience_router.post("/voices/pick")
def pick(req: VoicePickRequest) -> dict:
    """Pick a sensible default voice for a pillar / persona."""
    return pick_voice(pillar=req.pillar, persona=req.persona).as_dict()


@audience_router.get("/hooks/types")
def hook_types() -> dict:
    """The ten hook types and the six scoring axes."""
    return {
        "hook_types": [{"type": t, "brief": b} for t, b in HOOK_TYPES],
        "score_axes": list(SCORE_AXES),
    }


@audience_router.post("/hooks/lab")
def hooks_lab(req: HookLabRequest) -> dict:
    """Generate ten hooks for a topic, score them, return them best-first."""
    label = ""
    if req.persona:
        p = get_persona(req.persona)
        label = p.label if p else ""
    result = HookLab().run(req.topic, platform=req.platform, persona_label=label)
    return result.as_dict()
