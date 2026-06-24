"""The 5090 Studio Engine — local, offline content generation.

This is the engine the **Studio Worker** (the 5090 box) runs at an expo or on a
plane: it generates strong, reviewable, exportable content *entirely locally*. It
needs no server, no PWA backend, and no Instagram/TikTok connection.

It composes the engines that already exist —
:class:`~invisable_os.engines.generator.Generator` (which degrades to safe,
original templates with no model), the hard-gate
:func:`~invisable_os.guardrails.engine.check`, the values
:class:`~invisable_os.engines.scoring.Scorer`, the
:class:`~invisable_os.engines.mission.MissionEngine`, and the
:func:`~invisable_os.engines.personality.personality_score` — and turns each raw
candidate into a fully-formed :class:`~invisable_os.models.studio.StudioPost`:
caption, hashtags, script, visual idea, founder-presence suggestion, and the four
editorial scores (risk, mission, humour, authenticity).

Batches map to the Studio app's buttons:

    daily20  →  "Generate 20 Posts"        humour  →  "Generate Humour Batch"
    awareness → "Generate Awareness Batch"  founder → "Generate Founder Posts"
    trend     → "Generate Trend Reaction"
"""

from __future__ import annotations

from dataclasses import dataclass

from invisable_os.engines.generator import Generator
from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.personality import personality_score
from invisable_os.engines.scoring import Scorer
from invisable_os.guardrails.engine import check, swear_level
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform
from invisable_os.models.studio import StudioPost, StudioScores, StudioStatus


@dataclass(frozen=True)
class BatchSpec:
    """A recipe for one kind of batch: which brief, pillar, angle and platform."""

    key: str
    label: str
    pillar: str
    platform: Platform
    content_format: ContentFormat
    brief: str
    angle: str
    founder_centred: bool = False


# The five expo batches. Each maps to a button in the Studio app.
BATCHES: dict[str, BatchSpec] = {
    "humour": BatchSpec(
        key="humour",
        label="Humour Batch",
        pillar="humour",
        platform=Platform.TIKTOK,
        content_format=ContentFormat.SHORT_VIDEO,
        brief="Warm, self-deprecating British humour about living with invisible illness",
        angle="gentle_humour",
    ),
    "awareness": BatchSpec(
        key="awareness",
        label="Awareness Batch",
        pillar="education",
        platform=Platform.INSTAGRAM,
        content_format=ContentFormat.CAROUSEL,
        brief="Teach one concrete, honest thing about living with invisible illness",
        angle="explainer",
    ),
    "founder": BatchSpec(
        key="founder",
        label="Founder Posts",
        pillar="founder",
        platform=Platform.INSTAGRAM,
        content_format=ContentFormat.SHORT_VIDEO,
        brief="Stephen's genuine advocacy and why INVISABLE exists",
        angle="founder_voice",
        founder_centred=True,
    ),
    "trend": BatchSpec(
        key="trend",
        label="Trend Reaction",
        pillar="trends",
        platform=Platform.TIKTOK,
        content_format=ContentFormat.SHORT_VIDEO,
        brief="A genuine reaction to a current trend, tied honestly back to the mission",
        angle="community_prompt",
    ),
    "community": BatchSpec(
        key="community",
        label="Trades / Community",
        pillar="community",
        platform=Platform.INSTAGRAM,
        content_format=ContentFormat.TEXT_POST,
        brief="A relatable moment for tradespeople living with invisible illness",
        angle="solidarity",
    ),
}

# The mix for the 20-post daily batch (sums to 20). Mirrors the Daily Director's
# editorial brief, expressed as which batch recipe fills each slot.
DAILY20_MIX: list[str] = (
    ["awareness"] * 4
    + ["community"] * 4
    + ["humour"] * 5
    + ["trend"] * 3
    + ["founder"] * 4
)

# Hashtag vocabulary — clean, honest, on-mission. No fake claims, no spammy tag walls.
_BASE_TAGS = ("#INVISABLE", "#InvisibleIllness", "#InvisibleIllnessAwareness")
_PILLAR_TAGS: dict[str, tuple[str, ...]] = {
    "humour": ("#ChronicIllnessHumour", "#SpoonieLife", "#BritishHumour"),
    "education": ("#ChronicIllness", "#Spoonie", "#HealthAwareness"),
    "community": ("#TradesCommunity", "#Tradespeople", "#YouAreNotAlone"),
    "founder": ("#FounderStory", "#BuildInPublic", "#WhyIStarted"),
    "trends": ("#Relatable", "#ChronicIllness", "#OnTrend"),
}


class StudioEngine:
    """Generates fully-formed, locally reviewable content batches — offline-first."""

    def __init__(
        self,
        generator: Generator | None = None,
        scorer: Scorer | None = None,
        mission: MissionEngine | None = None,
    ) -> None:
        self.generator = generator or Generator()
        self.scorer = scorer or Scorer()
        self.mission = mission or MissionEngine()

    # -- public API ----------------------------------------------------------

    def generate_batch(self, batch: str, count: int | None = None) -> list[StudioPost]:
        """Generate a named batch of fully-formed posts.

        ``batch`` is one of ``daily20`` or a key in :data:`BATCHES`. ``count``
        overrides the default size (ignored for ``daily20``, which is always 20).
        """
        if batch == "daily20":
            return self.generate_daily20()
        spec = BATCHES.get(batch)
        if spec is None:
            raise ValueError(f"Unknown batch: {batch!r}")
        n = count if count is not None else 6
        return self._build_many(spec, n)

    def generate_daily20(self) -> list[StudioPost]:
        """The full 20-post daily batch, mixed across pillars per the editorial brief."""
        posts: list[StudioPost] = []
        for i, key in enumerate(DAILY20_MIX):
            spec = BATCHES[key]
            posts.append(self._build_one(spec, variant=i, batch="daily20"))
        return posts

    # -- internals -----------------------------------------------------------

    def _build_many(self, spec: BatchSpec, count: int) -> list[StudioPost]:
        return [self._build_one(spec, variant=i, batch=spec.key) for i in range(count)]

    def _build_one(self, spec: BatchSpec, *, variant: int, batch: str) -> StudioPost:
        # 1. Generate a single candidate in this batch's angle (offline → safe template).
        candidates = self.generator.generate(
            spec.brief,
            spec.platform,
            count=1,
            content_format=spec.content_format,
            angle=spec.angle,
        )
        cand = candidates[0]
        # The generator decides founder-centring from the angle; honour the spec too.
        if spec.founder_centred:
            cand.founder_centred = True

        # 2. Gate + score.
        verdict = check(cand)
        card = self.scorer.score(cand)
        mission = self.mission.advise(cand)

        # 3. The four editorial scores.
        #    Humour blends measured wit (lexical markers + brand voice) with a light
        #    prior for the humour pillar, whose posts are comedic by construction — so
        #    a flat-feeling humour post still reads as "humour, but punch it up", not 0.
        humour = 0.6 * card.humour + 0.4 * personality_score(cand.full_text)
        if spec.pillar == "humour":
            humour = max(humour, 0.4)
        humour = round(min(1.0, humour), 3)
        scores = StudioScores(
            risk=self._risk_score(verdict, cand.full_text),
            mission=mission.total(),
            humour=humour,
            authenticity=card.authenticity,
        )

        # 4. Enrich into a fully-formed, exportable post.
        return StudioPost(
            batch=batch,
            pillar=spec.pillar,
            status=StudioStatus.GENERATED,
            platform=cand.platform,
            format=cand.content_format,
            hook=cand.hook,
            caption=self._caption(cand),
            hashtags=self._hashtags(spec, cand),
            script=self._script(cand),
            visual_idea=self._visual_idea(spec, cand),
            founder_presence_suggestion=self._founder_suggestion(spec, cand),
            scores=scores,
            founder_centred=cand.founder_centred,
            original=cand.original,
            themes=cand.themes,
            generator=cand.generator,
            rationale=mission.rationale,
            needs_human_review=verdict.needs_human_review,
            notes=list(verdict.violations) if verdict.blocked else [],
        )

    # -- scoring helpers -----------------------------------------------------

    @staticmethod
    def _risk_score(verdict, text: str) -> float:
        """0.0 (safe) → 1.0 (blocked). Advisory flags and profanity raise it gently."""
        if verdict.blocked:
            return 1.0
        risk = 0.15 * len(verdict.risk_flags)
        bump = {"none": 0.0, "light": 0.05, "moderate": 0.12, "strong": 0.2}
        risk += bump.get(swear_level(text), 0.0)
        return round(min(risk, 0.9), 3)

    # -- enrichment helpers (deterministic, offline-safe) --------------------

    @staticmethod
    def _caption(cand: ContentCandidate) -> str:
        """A ready-to-paste caption: body, then the call to action on its own line."""
        parts = [p for p in (cand.body.strip(), cand.call_to_action.strip()) if p]
        return "\n\n".join(parts)

    @staticmethod
    def _hashtags(spec: BatchSpec, cand: ContentCandidate) -> list[str]:
        tags = list(_BASE_TAGS) + list(_PILLAR_TAGS.get(spec.pillar, ()))
        # De-duplicate while preserving order; keep it tight (max 8 — no tag walls).
        seen: set[str] = set()
        out: list[str] = []
        for t in tags:
            low = t.lower()
            if low not in seen:
                seen.add(low)
                out.append(t)
        return out[:8]

    @staticmethod
    def _script(cand: ContentCandidate) -> str:
        """A short, filmable 3-beat script built from hook / body / CTA."""
        hook = cand.hook.strip() or "Open on an honest, real moment."
        body = cand.body.strip() or "Say the true thing, plainly and kindly."
        cta = cand.call_to_action.strip() or "Invite the community in — gently."
        if cand.content_format in (ContentFormat.SHORT_VIDEO, ContentFormat.LONG_VIDEO):
            return (
                f"[0:00 HOOK] {hook}\n"
                f"[0:02 BEAT] {body}\n"
                f"[0:12 TURN] Let it land — a beat of honest eye-contact, no overclaiming.\n"
                f"[0:15 CTA] {cta}"
            )
        if cand.content_format == ContentFormat.CAROUSEL:
            return (
                f"Slide 1 (hook): {hook}\n"
                f"Slide 2–4 (explain): {body}\n"
                f"Slide 5 (CTA): {cta}"
            )
        # Static / text formats: a simple read-through script.
        return f"Read-to-camera or caption-on-screen:\n{hook}\n{body}\n{cta}"

    @staticmethod
    def _visual_idea(spec: BatchSpec, cand: ContentCandidate) -> str:
        ideas = {
            "humour": "Handheld piece-to-camera, natural light, a wry deadpan delivery; "
            "on-screen caption with the punchline mistimed for comic effect.",
            "education": "Clean carousel: bold myth on slide 1, calm reality on the rest; "
            "muted brand palette, generous whitespace, one idea per slide.",
            "community": "Real workplace / van / site B-roll; honest, unpolished texture; "
            "caption-on-screen so it reads with sound off.",
            "founder": "Stephen piece-to-camera in a real setting (workshop/home), "
            "soft natural light, eye-line to lens; no studio gloss.",
            "trends": "React-style split or stitch frame; keep the reaction warm and "
            "on-mission, never mocking; subtitle every line.",
        }
        return ideas.get(spec.pillar, "Simple, honest visual that matches the words on screen.")

    @staticmethod
    def _founder_suggestion(spec: BatchSpec, cand: ContentCandidate) -> str:
        if cand.founder_centred or spec.founder_centred:
            return (
                "Stephen on camera, first-person — this is his voice. Keep it genuine: "
                "his real advocacy, no scripted-sounding lines, no fabricated stories."
            )
        if spec.pillar == "humour":
            return "Optional Stephen cameo or voiceover for warmth; works without him too."
        return (
            "Founder-light: Stephen as a closing voiceover or end-card sign-off keeps "
            "presence high across the day without forcing him into every post."
        )
