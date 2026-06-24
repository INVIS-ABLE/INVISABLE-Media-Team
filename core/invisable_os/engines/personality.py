"""Humour & Personality Engine.

The INVISABLE® brand must not be sterile, corporate, or overly cautious. This
engine gives content a consistent, human, British personality and rotates styles
so the output never feels repetitive.

The hard brand-safety line (slurs, harassment, punching down) lives in
:mod:`invisable_os.guardrails`. This engine handles the *positive* side: which
personality style to use, the content-pillar mix, and scoring how well a piece
lands the brand's voice.

Allowed humour: self-deprecating, situational, shared-frustration, trades banter,
about the founder's own experience. Never at the expense of vulnerable people.
"""

from __future__ import annotations

from enum import StrEnum

from invisable_os.guardrails import swear_level


class PersonalityStyle(StrEnum):
    """The voices the brand rotates through."""

    BRITISH_DRY = "british_dry"
    SELF_DEPRECATING = "self_deprecating"
    TRADES_BANTER = "trades_banter"
    SARCASM = "sarcasm"
    OBSERVATIONAL = "observational"
    FRUSTRATION = "frustration"
    RELATABLE = "relatable"
    WARM_SERIOUS = "warm_serious"
    EDUCATIONAL = "educational"
    FOUNDER = "founder"


class ContentPillar(StrEnum):
    """The content mix the brand publishes against."""

    HUMOUR = "humour"
    EDUCATION = "education"
    COMMUNITY = "community"
    FOUNDER = "founder"
    PARTNER = "partner"
    TRENDS = "trends"
    CAMPAIGNS = "campaigns"


# The personality mix (must sum to 1.0). Humour leads, but education and community
# carry the mission. Founder voice is ~10% here; the Founder Engine separately
# ensures founder *presence* (a broader concept) reaches ~80%.
CONTENT_PERSONALITY_MIX: dict[ContentPillar, float] = {
    ContentPillar.HUMOUR: 0.30,
    ContentPillar.EDUCATION: 0.25,
    ContentPillar.COMMUNITY: 0.20,
    ContentPillar.FOUNDER: 0.10,
    ContentPillar.PARTNER: 0.05,
    ContentPillar.TRENDS: 0.05,
    ContentPillar.CAMPAIGNS: 0.05,
}

# Example hooks that capture the allowed voice — self-deprecating & situational.
VOICE_EXEMPLARS: tuple[str, ...] = (
    "My immune system called in sick before I did.",
    "The van starts more reliably than I do.",
    "Tool theft wasn't enough, so my body joined in.",
)

# Markers of authentic personality (used for a light voice score).
PERSONALITY_MARKERS: tuple[str, ...] = (
    "honestly",
    "let's be honest",
    "proper",
    "mate",
    "knackered",
    "nightmare",
    "the audacity",
    "nobody warned me",
    "turns out",
    "apparently",
)


def rotate_styles(n: int, *, start: int = 0) -> list[PersonalityStyle]:
    """Return ``n`` personality styles in rotation, to avoid repetitive output."""
    styles = list(PersonalityStyle)
    return [styles[(start + i) % len(styles)] for i in range(n)]


def pillar_targets(total_posts: int) -> dict[ContentPillar, int]:
    """Distribute ``total_posts`` across pillars per the personality mix."""
    counts = {p: int(round(total_posts * share)) for p, share in CONTENT_PERSONALITY_MIX.items()}
    # Fix rounding drift so the counts sum exactly to total_posts.
    drift = total_posts - sum(counts.values())
    if drift:
        # Apply the drift to the largest pillar (humour) to keep proportions sane.
        counts[ContentPillar.HUMOUR] += drift
    return counts


def personality_score(text: str) -> float:
    """0.0–1.0 measure of how much authentic brand personality the text carries."""
    lowered = text.lower()
    hits = sum(1 for m in PERSONALITY_MARKERS if m in lowered)
    return round(min(hits / 3.0, 1.0), 3)


def describe_swearing(text: str) -> str:
    """Human-readable note about profanity level and whether it's acceptable.

    Swearing is allowed when natural and British in register; targeting is already
    blocked by the guardrails, so any swearing that survives the gate is acceptable
    — this just records its strength for editorial awareness.
    """
    level = swear_level(text)
    if level == "none":
        return "no profanity"
    return f"{level} profanity (allowed — natural register; no target detected)"
