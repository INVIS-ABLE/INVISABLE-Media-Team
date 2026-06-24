"""Cultural Intelligence Engine.

Understands British culture, humour, trades culture, football culture, and the way
things are actually said — so content lands as authentic rather than imported. It
contributes a *cultural resonance* signal to scoring and supplies context that the
generator can use. Notes accumulate in ``INVISABLE_BRAIN`` under ``cultural_note``.

Importantly, this engine encodes *register and tone*, never stereotypes. The goal
is content that feels genuinely British and warm, not caricature.
"""

from __future__ import annotations

from invisable_os.brain import Memory, get_brain

# Markers of natural British register. Presence is a positive resonance signal;
# absence is neutral (not penalised) — plain, clear English is always fine.
BRITISH_REGISTER = (
    "fortnight",
    "brilliant",
    "proper",
    "cuppa",
    "mate",
    "knackered",
    "chuffed",
    "gutted",
    "sound",
    "graft",
    "having a mare",
    "fair play",
    "spot on",
    "the lads",
    "down the pub",
    "bank holiday",
)

# Domains the engine is fluent in, with light context for the generator.
CULTURAL_DOMAINS = {
    "trades": (
        "Tradespeople (builders, sparkies, plumbers, chippies). Early starts, graft, "
        "dry humour, pride in the work, looking out for the lads on site. Invisible "
        "illness is common and rarely talked about here — a key audience to reach with "
        "respect, never pity."
    ),
    "football": (
        "Football culture — matchday, the local club, terrace humour, loyalty. A shared "
        "language for resilience and community that maps naturally onto the movement."
    ),
    "humour": (
        "British humour: self-deprecating, understated, dry, warm. Never punching down. "
        "Humour is used to disarm and connect, never to mock the illness or the person."
    ),
    "everyday": (
        "Everyday British life — the commute, the weather, the cuppa, the group chat. "
        "Grounding the message in the ordinary makes invisible illness relatable."
    ),
}

# Americanisms to gently flag so copy stays British.
AMERICANISMS = {
    "gotten": "got",
    "color": "colour",
    "favorite": "favourite",
    "diaper": "nappy",
    "vacation": "holiday",
    "sidewalk": "pavement",
    "fall": "autumn",
    "soccer": "football",
    "z's": "z (use British spelling)",
}


class CulturalIntelligenceEngine:
    """Scores cultural resonance and supplies context for generation."""

    def __init__(self) -> None:
        self.brain = get_brain()

    def context_for(self, brief: str) -> str:
        """Return a compact cultural briefing relevant to ``brief``."""
        lowered = brief.lower()
        relevant = [
            f"- {domain}: {ctx}"
            for domain, ctx in CULTURAL_DOMAINS.items()
            if domain in lowered or domain == "humour" or domain == "everyday"
        ]
        recalled = self.brain.recall(brief, kind="cultural_note", limit=3)
        notes = [f"- learned: {m.text}" for m in recalled]
        return "\n".join(["British cultural context:", *relevant, *notes])

    def resonance(self, text: str) -> tuple[float, list[str]]:
        """Return a 0.0–1.0 cultural-resonance score and human-readable notes.

        Rewards natural British register; flags Americanisms. Plain clear English
        scores a neutral-positive baseline — we never *require* slang.
        """
        lowered = text.lower()
        notes: list[str] = []

        hits = sum(1 for m in BRITISH_REGISTER if m in lowered)
        register_score = min(hits / 3.0, 1.0)  # 3+ natural markers saturates

        americanisms = [a for a in AMERICANISMS if a in lowered.split()]
        if americanisms:
            notes.append(
                "Americanisms to swap for British English: "
                + ", ".join(f"{a}→{AMERICANISMS[a]}" for a in americanisms)
            )

        # Baseline 0.55 so clear, plain copy is never punished; register lifts it,
        # americanisms gently pull it down.
        score = 0.55 + 0.45 * register_score - 0.1 * len(americanisms)
        score = max(0.0, min(1.0, score))
        if hits:
            notes.append(f"{hits} natural British register marker(s) detected.")
        return round(score, 3), notes

    def learn(self, note: str, **metadata) -> str:
        """Record a cultural learning into the Brain."""
        return self.brain.remember(Memory(text=note, kind="cultural_note", metadata=metadata))
