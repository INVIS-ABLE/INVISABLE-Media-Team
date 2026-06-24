"""The Hook Laboratory — generate many hooks, score them, pick the strongest.

For every post the lab produces ten hooks across distinct hook *types* (shock truth,
funny pain, POV, confession, myth-bust, trades banter, founder raw, question,
stitch/reaction, "nobody talks about…"), scores each on six axes, and returns them
ranked with the winner first.

Generation uses the shared LLM client when configured and degrades to deterministic,
on-brand templates per hook type offline — so the lab always returns ten scored hooks
and the whole thing is testable with no model. Scoring is deterministic keyword/shape
analysis: fast, transparent, and never "talked around" by a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from invisable_os.llm import get_llm

# The ten hook types. Each carries a short brief (steers the LLM) and an offline
# template that turns a topic into an original, on-brand hook of that type.
HOOK_TYPES: tuple[tuple[str, str], ...] = (
    ("shock_truth", "A hard, true line that stops the scroll. No clickbait, no overclaim."),
    ("funny_pain", "Warm, self-deprecating humour about the daily reality. Laugh WITH."),
    ("pov", "A 'POV:' framing that drops the viewer straight into the moment."),
    ("confession", "An honest, first-person admission that earns trust."),
    ("myth_bust", "Name a common misconception, then flip it — kindly."),
    ("trades_banter", "Dry site humour the trades instantly get."),
    ("founder_raw", "The founder, unfiltered, on why this matters."),
    ("question", "A direct question that makes the viewer answer in their head."),
    ("stitch_reaction", "A reaction framing that invites a stitch/duet (platform-native)."),
    ("nobody_talks", "'Nobody talks about…' — surface the unsaid part."),
)

_HOOK_TYPE_KEYS = tuple(t for t, _ in HOOK_TYPES)

# Scoring lexicons (deterministic). Small and transparent by design.
_CURIOSITY = ("nobody", "the truth", "what no one", "secret", "actually", "really",
              "why", "how", "the bit", "you didn't")
_EMOTION = ("alone", "unseen", "hurts", "exhausted", "proud", "scared", "matter",
            "strength", "fear", "honest", "real")
_HUMOUR = ("nap", "battery", "2%", "banter", "lol", "me trying", "pov", "when you",
           "handed in its notice", "forecast")
_SHARE = ("send this", "tag", "save this", "share", "someone who", "if this is you",
          "we've all", "every")
_MISSION = ("invisible illness", "chronic", "trades", "invisable", "unseen", "looking fine",
            "disability", "fatigue", "site")


@dataclass
class ScoredHook:
    text: str
    hook_type: str
    scores: dict[str, float]
    total: float

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "hook_type": self.hook_type,
            "scores": self.scores,
            "total": self.total,
        }


@dataclass
class HookLabResult:
    topic: str
    platform: str
    best: ScoredHook
    hooks: list[ScoredHook] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "topic": self.topic,
            "platform": self.platform,
            "best": self.best.as_dict(),
            "hooks": [h.as_dict() for h in self.hooks],
        }


# The six scoring axes, in the spec's order.
SCORE_AXES = ("curiosity", "emotion", "humour", "shareability", "platform_fit", "mission_fit")


def _frac(text: str, words: tuple[str, ...]) -> float:
    lowered = text.lower()
    hits = sum(1 for w in words if w in lowered)
    return 0.0 if hits == 0 else round(min(1.0, 1 - 0.55**hits), 3)


def _platform_fit(text: str, platform: str, hook_type: str) -> float:
    """Short hooks fit short-form; some types are platform-native."""
    words = len(text.split())
    fit = 1.0 if words <= 12 else 0.7 if words <= 18 else 0.4
    native = hook_type in ("pov", "stitch_reaction", "funny_pain")
    if platform in ("tiktok", "instagram") and native:
        fit = min(1.0, fit + 0.1)
    return round(fit, 3)


def score_hook(text: str, hook_type: str, *, platform: str = "tiktok") -> ScoredHook:
    """Score one hook on the six axes and a weighted total."""
    scores = {
        "curiosity": _frac(text, _CURIOSITY),
        "emotion": _frac(text, _EMOTION),
        "humour": _frac(text, _HUMOUR),
        "shareability": _frac(text, _SHARE),
        "platform_fit": _platform_fit(text, platform, hook_type),
        "mission_fit": _frac(text, _MISSION),
    }
    # Weighted: curiosity + platform-fit carry the scroll-stop; mission keeps us on-brand.
    total = round(
        0.25 * scores["curiosity"]
        + 0.18 * scores["emotion"]
        + 0.14 * scores["humour"]
        + 0.16 * scores["shareability"]
        + 0.15 * scores["platform_fit"]
        + 0.12 * scores["mission_fit"],
        4,
    )
    return ScoredHook(text=text, hook_type=hook_type, scores=scores, total=total)


class HookLab:
    """Generates and scores a field of hooks for a topic."""

    def __init__(self) -> None:
        self.llm = get_llm()

    def run(
        self, topic: str, *, platform: str = "tiktok", persona_label: str = ""
    ) -> HookLabResult:
        """Produce ten scored hooks for ``topic`` and return them best-first."""
        texts = self._generate(topic, platform, persona_label)
        scored = [score_hook(t, htype, platform=platform) for htype, t in texts]
        scored.sort(key=lambda h: h.total, reverse=True)
        return HookLabResult(topic=topic, platform=platform, best=scored[0], hooks=scored)

    # -- generation ----------------------------------------------------------

    def _generate(self, topic: str, platform: str, persona_label: str) -> list[tuple[str, str]]:
        system = (
            "You are INVISABLE OS's Hook Laboratory for the INVISABLE® movement "
            "(invisible illness, trades, British humour). Write original hooks only — "
            "scroll-stopping but never clickbait, never overclaiming, never punching down."
        )
        audience = f" Target audience: {persona_label}." if persona_label else ""
        prompt = (
            f"Topic: {topic}\nPlatform: {platform}.{audience}\n"
            "Write one hook for each of these types: "
            + ", ".join(_HOOK_TYPE_KEYS)
            + ". Keep each hook under 14 words."
        )
        resp = self.llm.complete_json(
            prompt, system=system, schema_hint=", ".join(_HOOK_TYPE_KEYS),
            max_tokens=500, prefer_fast=True,
        )
        data = resp.data or {}
        out: list[tuple[str, str]] = []
        for htype, _brief in HOOK_TYPES:
            text = str(data.get(htype, "")).strip()
            if not text:
                text = _template(htype, topic)
            out.append((htype, text))
        return out


def _template(hook_type: str, topic: str) -> str:
    """Deterministic, original, on-brand hook per type."""
    subject = (topic or "this").strip().rstrip(".")
    s = subject.lower()
    templates = {
        "shock_truth": f"You can be exhausted to the bone and still 'look fine'. That's {s}.",
        "funny_pain": f"My body, an honest forecast on {s}: cloudy with a chance of nap.",
        "pov": f"POV: it's 7am, the job's waiting, and {s} has other plans.",
        "confession": f"I masked {s} for years because I thought no one would believe me.",
        "myth_bust": f"'But you don't look ill.' Here's what {s} actually looks like.",
        "trades_banter": f"When the lads ask why you're quiet and it's really {s}.",
        "founder_raw": f"I built INVISABLE because nobody was saying the truth about {s}.",
        "question": f"What would you do if {s} hit halfway through a shift?",
        "stitch_reaction": f"Stitch this if {s} has ever made you cancel plans last minute.",
        "nobody_talks": f"Nobody talks about the part of {s} that happens after everyone leaves.",
    }
    return templates.get(hook_type, f"The bit you don't see about {s}.")
