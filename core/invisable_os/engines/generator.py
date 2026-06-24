"""Candidate generation.

At volume ("hundreds of candidates daily") generation is driven by the LLM layer.
Offline, it degrades to a deterministic, varied set of *safe, original* templates so
the tournament always has a field to compete — and so the whole pipeline is testable
without any model. The templates are scaffolds of structure and angle, never copied
content, and never fabricated founder experiences.
"""

from __future__ import annotations

from invisable_os.engines.cultural import CulturalIntelligenceEngine
from invisable_os.llm import get_llm
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform

# Angles are *structural* scaffolds — distinct ways to frame a true message. They
# are deliberately generic so the real, specific content is filled in by the model
# or by the human founder; they never assert a fabricated experience.
ANGLES = (
    ("myth_vs_reality", "Name a common misconception, then the reality — kindly."),
    ("explainer", "Teach one concrete thing about living with invisible illness."),
    ("solidarity", "Speak directly to someone who feels unseen today."),
    ("gentle_humour", "Use warm, self-deprecating British humour to disarm, never mock."),
    ("founder_voice", "Share the founder's genuine advocacy and why INVISABLE exists."),
    ("practical_tip", "Offer one practical, honest, non-medical coping idea."),
    ("community_prompt", "Invite the community to share their experience respectfully."),
    ("reframe", "Reframe an everyday moment to reveal the invisible struggle behind it."),
)


class Generator:
    """Produces a field of candidate content for a brief."""

    def __init__(self, cultural: CulturalIntelligenceEngine | None = None) -> None:
        self.cultural = cultural or CulturalIntelligenceEngine()
        self.llm = get_llm()

    def generate(
        self,
        brief: str,
        platform: Platform,
        count: int = 24,
        content_format: ContentFormat = ContentFormat.SHORT_VIDEO,
        angle: str | None = None,
    ) -> list[ContentCandidate]:
        """Return ``count`` candidate pieces for ``brief``.

        If ``angle`` is given, every candidate is generated in that angle (used by the
        Daily Director so each slot produces content matching its editorial intent);
        otherwise the generator rotates through all angles.
        """
        candidates: list[ContentCandidate] = []
        cultural_context = self.cultural.context_for(brief)
        angle_map = dict(ANGLES)

        for i in range(count):
            if angle and angle in angle_map:
                angle_key, angle_desc = angle, angle_map[angle]
            else:
                angle_key, angle_desc = ANGLES[i % len(ANGLES)]
            founder_centred = angle_key == "founder_voice"
            candidate = self._one(
                brief=brief,
                platform=platform,
                content_format=content_format,
                angle_key=angle_key,
                angle_desc=angle_desc,
                cultural_context=cultural_context,
                founder_centred=founder_centred,
                variant=i,
            )
            candidates.append(candidate)
        return candidates

    def _one(
        self,
        *,
        brief: str,
        platform: Platform,
        content_format: ContentFormat,
        angle_key: str,
        angle_desc: str,
        cultural_context: str,
        founder_centred: bool,
        variant: int,
    ) -> ContentCandidate:
        system = (
            "You are INVISABLE OS's content generator for the INVISABLE® movement, "
            "raising awareness of invisible illness. Write original content only. "
            "Never fabricate stories, testimonials, or founder experiences. "
            "Optimise for trust, awareness, authenticity, education, warmth and "
            "British humour. Avoid controversy, outrage, spam and engagement-bait."
        )
        prompt = (
            f"Brief: {brief}\n"
            f"Platform: {platform.value}; Format: {content_format.value}\n"
            f"Angle: {angle_desc}\n"
            f"{cultural_context}\n\n"
            "Return a hook line, a short body, and a gentle call to action."
        )
        response = self.llm.complete(prompt, system=system, max_tokens=400, prefer_fast=True)

        if response.backend == "stub":
            hook, body, cta = self._template(brief, angle_key, founder_centred, variant)
        else:
            hook, body, cta = self._parse(response.text, brief, angle_key, founder_centred)

        return ContentCandidate(
            brief=brief,
            platform=platform,
            content_format=content_format,
            hook=hook,
            body=body,
            call_to_action=cta,
            founder_centred=founder_centred,
            original=True,
            themes=[angle_key, "invisible_illness"],
            generator=f"{response.backend}:{response.model}",
        )

    # -- offline templates: safe, original scaffolds -------------------------

    def _template(
        self, brief: str, angle_key: str, founder_centred: bool, variant: int
    ) -> tuple[str, str, str]:
        subject = brief.strip().rstrip(".")
        templates = {
            "myth_vs_reality": (
                "“But you don't look ill.”",
                f"Here's the thing about {subject.lower()}: looking fine and being fine "
                "are not the same. Invisible illness is invisible — that's the whole point.",
                "If you've heard that line too, you're not alone.",
            ),
            "explainer": (
                f"One thing most people get wrong about {subject.lower()}.",
                f"Let me explain it plainly: {subject}. It's not laziness and it's not a "
                "choice — it's a real, daily reality for millions.",
                "Save this to share with someone who needs to understand.",
            ),
            "solidarity": (
                "If today felt heavier than it looked, this is for you.",
                f"{subject}. You got through it. That counts, even if no one saw it.",
                "Tell us how today went — we're listening.",
            ),
            "gentle_humour": (
                "My energy levels, an honest forecast: cloudy with a chance of nap.",
                f"{subject}. We laugh because it's real — and because a bit of warmth "
                "makes the hard days lighter.",
                "Drop a comment if your battery's on 2% as well.",
            ),
            "founder_voice": (
                "Why I started INVISABLE.",
                f"As the founder, I care about this because it's real: {subject}. "
                "INVISABLE exists to make the unseen seen — honestly, with no overclaiming.",
                "Follow along as we build this with the community.",
            ),
            "practical_tip": (
                "One small thing that genuinely helps.",
                f"Not medical advice, just honest: {subject}. Pacing beats pushing through. "
                "Small, kind adjustments add up.",
                "What helps you? Share it for someone who needs it.",
            ),
            "community_prompt": (
                "A question for anyone who lives with this.",
                f"{subject}. Your experience matters and it helps others feel less alone.",
                "If this is you, share your story — only if you want to.",
            ),
            "reframe": (
                "The bit you didn't see.",
                f"Behind an ordinary moment: {subject}. The struggle is invisible, but it's "
                "there — and naming it changes things.",
                "Send this to someone who'd recognise it.",
            ),
        }
        hook, body, cta = templates.get(angle_key, templates["explainer"])
        # Light variation so a field isn't identical, without changing meaning.
        if variant % 3 == 1:
            cta = cta.rstrip(".") + "."
        return hook, body, cta

    def _parse(
        self, text: str, brief: str, angle_key: str, founder_centred: bool
    ) -> tuple[str, str, str]:
        """Best-effort parse of a model response into hook/body/cta."""
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        if not lines:
            return self._template(brief, angle_key, founder_centred, 0)
        hook = lines[0]
        cta = lines[-1] if len(lines) > 1 else ""
        body = " ".join(lines[1:-1]) if len(lines) > 2 else (lines[1] if len(lines) > 1 else "")
        return hook, body, cta
