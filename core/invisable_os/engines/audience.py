"""Audience Command — who is watching, and in whose voice we answer.

Two registries the rest of the platform targets against:

* **Audience personas** — the eight people INVISABLE® makes content for. Every post
  should target one *primary* persona; :func:`target_persona` scores a piece of text
  against the personas so the system can label (or re-target) it deterministically.
* **Creator voice bank** — nine stored voice modes so the feed never sounds samey.
  :func:`pick_voice` chooses a sensible default voice for a persona + pillar.

Everything here is deterministic and dependency-free — pure registries and keyword
scoring — so it is fast, fully testable, and never "talked around" by a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AudiencePersona(StrEnum):
    """The eight audiences every post is made for."""

    TRADES_INVISIBLE_ILLNESS = "trades_invisible_illness"
    SELF_EMPLOYED_BUILDER = "self_employed_builder"
    FAMILY_CARER = "family_carer"
    EMPLOYER_SITE_MANAGER = "employer_site_manager"
    SPONSOR_PARTNER = "sponsor_partner"
    GENERAL_PUBLIC = "general_public"
    YOUNG_CHRONIC_ILLNESS = "young_chronic_illness"
    CHARITY_SUPPORTER = "charity_supporter"


@dataclass(frozen=True)
class Persona:
    """A target audience: who they are, what they feel, where they watch."""

    id: AudiencePersona
    label: str
    description: str
    pains: tuple[str, ...]
    platforms: tuple[str, ...]
    tone: str
    keywords: tuple[str, ...]  # signals that a piece of content speaks to them

    def as_dict(self) -> dict:
        return {
            "id": self.id.value,
            "label": self.label,
            "description": self.description,
            "pains": list(self.pains),
            "platforms": list(self.platforms),
            "tone": self.tone,
        }


PERSONAS: tuple[Persona, ...] = (
    Persona(
        AudiencePersona.TRADES_INVISIBLE_ILLNESS,
        "Tradesperson with invisible illness",
        "Works a physical trade while managing a hidden condition.",
        ("being doubted", "pushing through pain", "fear of losing work"),
        ("tiktok", "instagram"),
        "solidarity, dry humour, no pity",
        ("trades", "site", "tools", "chronic", "fatigue", "pain", "flare", "invisible illness"),
    ),
    Persona(
        AudiencePersona.SELF_EMPLOYED_BUILDER,
        "Self-employed builder",
        "Runs their own trade; no sick pay, every day off costs money.",
        ("no sick pay", "cash-flow", "can't stop working", "tool/van theft"),
        ("tiktok", "instagram", "facebook"),
        "practical, straight-talking, respect for graft",
        ("self-employed", "subbie", "sole trader", "van", "tool theft", "quote", "cash flow"),
    ),
    Persona(
        AudiencePersona.FAMILY_CARER,
        "Family member / carer",
        "Loves someone with an invisible illness and wants to understand & help.",
        ("feeling helpless", "not knowing what to say", "burnout"),
        ("instagram", "facebook"),
        "warm, reassuring, practical",
        ("carer", "my partner", "my son", "my daughter", "family", "support", "look after"),
    ),
    Persona(
        AudiencePersona.EMPLOYER_SITE_MANAGER,
        "Employer / site manager",
        "Runs a site or team; needs the business case for reasonable adjustments.",
        ("retention", "absence", "legal duty", "productivity"),
        ("linkedin", "facebook"),
        "credible, evidence-led, non-preachy",
        ("employer", "site manager", "adjustments", "retention", "absence", "duty", "workforce"),
    ),
    Persona(
        AudiencePersona.SPONSOR_PARTNER,
        "Sponsor / partner",
        "A brand or partner (CT1, GT Insurance) aligning with the mission.",
        ("brand safety", "ROI", "authentic alignment"),
        ("linkedin", "instagram"),
        "professional, sponsor-safe, no false claims",
        ("sponsor", "partner", "brand", "ct1", "insurance", "campaign", "collaboration"),
    ),
    Persona(
        AudiencePersona.GENERAL_PUBLIC,
        "General public",
        "Scrolling by; doesn't know invisible illness is real until they feel it.",
        ("misconceptions", "'but you don't look ill'"),
        ("tiktok", "instagram"),
        "relatable, mythbusting, shareable",
        ("did you know", "myth", "most people", "everyone", "the truth about"),
    ),
    Persona(
        AudiencePersona.YOUNG_CHRONIC_ILLNESS,
        "Young person with chronic illness",
        "Newly diagnosed or growing up with a condition; wants to feel less alone.",
        ("isolation", "missing out", "masking", "uncertain future"),
        ("tiktok", "instagram"),
        "honest, hopeful, peer-to-peer, no lecturing",
        ("young", "diagnosed", "spoonie", "school", "uni", "felt alone", "growing up with"),
    ),
    Persona(
        AudiencePersona.CHARITY_SUPPORTER,
        "Charity supporter",
        "Backs the cause; donates, shares, shows up to campaigns.",
        ("wanting impact", "where the money goes"),
        ("instagram", "facebook"),
        "grateful, mission-led, transparent",
        ("donate", "support the cause", "fundraise", "awareness", "charity", "together"),
    ),
)

_PERSONA_BY_ID: dict[AudiencePersona, Persona] = {p.id: p for p in PERSONAS}
assert len(PERSONAS) == 8, "eight audience personas are specified"


def get_persona(persona: str | AudiencePersona) -> Persona | None:
    try:
        return _PERSONA_BY_ID[AudiencePersona(str(persona))]
    except (ValueError, KeyError):
        return None


@dataclass
class PersonaMatch:
    persona: AudiencePersona
    score: float
    runners_up: list[tuple[str, float]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "persona": self.persona.value,
            "label": _PERSONA_BY_ID[self.persona].label,
            "score": self.score,
            "runners_up": [{"persona": p, "score": s} for p, s in self.runners_up],
        }


def target_persona(text: str, *, platform: str = "") -> PersonaMatch:
    """Score ``text`` against the personas and return the best primary target.

    Deterministic keyword scoring with a light platform-fit nudge. Falls back to the
    general public when nothing else fits — there is always a primary persona.
    """
    lowered = (text or "").lower()
    scored: list[tuple[AudiencePersona, float]] = []
    for p in PERSONAS:
        hits = sum(1 for k in p.keywords if k in lowered)
        score = 0.0 if hits == 0 else min(0.95, 1 - 0.6**hits)
        if platform and platform in p.platforms:
            score += 0.05
        scored.append((p.id, round(score, 3)))
    scored.sort(key=lambda kv: kv[1], reverse=True)
    best, best_score = scored[0]
    if best_score == 0.0:
        best = AudiencePersona.GENERAL_PUBLIC
    runners = [(pid.value, sc) for pid, sc in scored[1:4]]
    return PersonaMatch(persona=best, score=best_score, runners_up=runners)


# ============================================================================
# Creator Voice Bank — nine stored voice modes so the feed isn't samey.
# ============================================================================


class VoiceMode(StrEnum):
    STEPHEN_RAW = "stephen_raw"
    INVISABLE_OFFICIAL = "invisable_official"
    TRADES_BANTER = "trades_banter"
    DARK_HUMOUR_SAFE = "dark_humour_safe"
    EMOTIONAL_CHARITY = "emotional_charity"
    SPONSOR_SAFE = "sponsor_safe"
    EDUCATIONAL = "educational"
    PISSED_OFF_PROFESSIONAL = "pissed_off_professional"
    HOPE_MISSION = "hope_mission"


@dataclass(frozen=True)
class Voice:
    id: VoiceMode
    label: str
    brief: str  # the persona/system brief that shapes this voice

    def as_dict(self) -> dict:
        return {"id": self.id.value, "label": self.label, "brief": self.brief}


VOICE_BANK: tuple[Voice, ...] = (
    Voice(VoiceMode.STEPHEN_RAW, "Stephen raw",
          "The founder, unfiltered and first person. Plain, honest, no corporate gloss; "
          "speak from lived conviction without inventing a specific event."),
    Voice(VoiceMode.INVISABLE_OFFICIAL, "INVISABLE official",
          "The brand voice: clear, warm, mission-led, dependable. Speaks for the movement."),
    Voice(VoiceMode.TRADES_BANTER, "Trades banter",
          "Site humour — dry, quick, in-jokes the trades get. Laughs WITH, never down."),
    Voice(VoiceMode.DARK_HUMOUR_SAFE, "Dark humour (safe)",
          "Gallows humour about the daily reality of illness — never about a person, "
          "never punching down, never near self-harm or tragedy."),
    Voice(VoiceMode.EMOTIONAL_CHARITY, "Emotional charity",
          "Sincere, moving, hopeful. For awareness and fundraising moments; no manipulation."),
    Voice(VoiceMode.SPONSOR_SAFE, "Sponsor-safe",
          "Brand-friendly: no false claims, no medical overclaims, no swearing; "
          "partner treated first-class."),
    Voice(VoiceMode.EDUCATIONAL, "Educational",
          "Calm, plain-English teaching. One concrete idea, no jargon, no overclaiming."),
    Voice(VoiceMode.PISSED_OFF_PROFESSIONAL, "Pissed-off but professional",
          "Righteous, controlled anger at injustice (doubt, discrimination). Firm, never abusive."),
    Voice(VoiceMode.HOPE_MISSION, "Hope / mission",
          "Forward-looking and galvanising — why this matters and where we're going."),
)

_VOICE_BY_ID: dict[VoiceMode, Voice] = {v.id: v for v in VOICE_BANK}
assert len(VOICE_BANK) == 9, "nine voice modes are specified"

# Sensible default voice per content pillar (the scheduler/generator can override).
_PILLAR_VOICE: dict[str, VoiceMode] = {
    "humour": VoiceMode.TRADES_BANTER,
    "education": VoiceMode.EDUCATIONAL,
    "community": VoiceMode.EMOTIONAL_CHARITY,
    "founder": VoiceMode.STEPHEN_RAW,
    "partner": VoiceMode.SPONSOR_SAFE,
    "trends": VoiceMode.INVISABLE_OFFICIAL,
    "campaigns": VoiceMode.HOPE_MISSION,
}


def get_voice(voice: str | VoiceMode) -> Voice | None:
    try:
        return _VOICE_BY_ID[VoiceMode(str(voice))]
    except (ValueError, KeyError):
        return None


def pick_voice(*, pillar: str = "", persona: str | AudiencePersona | None = None) -> Voice:
    """Choose a default voice for a pillar/persona. Always returns a voice."""
    if persona is not None:
        p = get_persona(persona)
        if p and p.id == AudiencePersona.SPONSOR_PARTNER:
            return _VOICE_BY_ID[VoiceMode.SPONSOR_SAFE]
        if p and p.id == AudiencePersona.EMPLOYER_SITE_MANAGER:
            return _VOICE_BY_ID[VoiceMode.EDUCATIONAL]
    return _VOICE_BY_ID[_PILLAR_VOICE.get(pillar, VoiceMode.INVISABLE_OFFICIAL)]
