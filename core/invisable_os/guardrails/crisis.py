"""Crisis / Sensitive Topic Mode — handle the heaviest subjects with extra care.

Some topics must never be treated like ordinary content. When a piece touches
suicide/self-harm, a death, illness deterioration, a hospital story, disability
discrimination, or benefits/legal trouble, the platform shifts into **crisis mode**:

* no jokes / no humour treatment,
* no clickbait hooks,
* a credible source is required,
* a human must approve it,
* and, where appropriate, **signpost** to real UK support (Samaritans, NHS 111, …).

This is a deterministic detector layered on top of the brand guardrails — advisory
in that it never silently blocks, but it raises hard *requirements* the rest of the
pipeline (and the approval UI) must honour before such content can go out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SensitiveTopic(StrEnum):
    SUICIDE_SELF_HARM = "suicide_self_harm"
    DEATH_BEREAVEMENT = "death_bereavement"
    ILLNESS_DETERIORATION = "illness_deterioration"
    HOSPITAL = "hospital"
    DISABILITY_DISCRIMINATION = "disability_discrimination"
    BENEFITS_LEGAL = "benefits_legal"
    ABUSE = "abuse"


# Phrase markers per sensitive topic. Whole-phrase, lowercase substring matching —
# transparent and conservative (favours catching a sensitive topic over missing one).
_TOPIC_MARKERS: dict[SensitiveTopic, tuple[str, ...]] = {
    SensitiveTopic.SUICIDE_SELF_HARM: (
        "suicide", "suicidal", "kill myself", "end my life", "take my own life",
        "self-harm", "self harm", "want to die", "don't want to be here",
    ),
    SensitiveTopic.DEATH_BEREAVEMENT: (
        "passed away", "died", "death", "lost my", "funeral", "grief", "bereaved",
        "we lost", "rip ", "no longer with us",
    ),
    SensitiveTopic.ILLNESS_DETERIORATION: (
        "getting worse", "deteriorating", "terminal", "end of life", "palliative",
        "won't get better", "declining", "relapse", "given months",
    ),
    SensitiveTopic.HOSPITAL: (
        "hospital", "intensive care", "icu", "a&e", "ambulance", "admitted",
        "surgery", "operation", "ward",
    ),
    SensitiveTopic.DISABILITY_DISCRIMINATION: (
        "discriminat", "sacked for", "fired because", "denied access", "refused work",
        "treated unfairly", "tribunal", "harassed at work",
    ),
    SensitiveTopic.BENEFITS_LEGAL: (
        "pip", "esa", "universal credit", "benefits stopped", "sanction", "appeal",
        "tribunal", "sue", "legal action", "solicitor",
    ),
    SensitiveTopic.ABUSE: (
        "abuse", "abused", "domestic violence", "assault", "groomed", "trafficking",
    ),
}

# UK signposting per topic. Real, stable national support lines.
_SIGNPOSTS: dict[SensitiveTopic, str] = {
    SensitiveTopic.SUICIDE_SELF_HARM: (
        "If you're struggling, Samaritans are there 24/7 — call 116 123 (free) or "
        "text SHOUT to 85258. In an emergency call 999."
    ),
    SensitiveTopic.DEATH_BEREAVEMENT: (
        "Bereavement support: Cruse Bereavement Support — 0808 808 1677."
    ),
    SensitiveTopic.ILLNESS_DETERIORATION: (
        "For health worries, NHS 111 can help; Marie Curie supports those with a "
        "terminal illness — 0800 090 2309."
    ),
    SensitiveTopic.HOSPITAL: (
        "For urgent medical help use NHS 111; in an emergency call 999."
    ),
    SensitiveTopic.DISABILITY_DISCRIMINATION: (
        "Free, confidential advice on disability rights at work: Acas — 0300 123 1100; "
        "or Scope's helpline — 0808 800 3333."
    ),
    SensitiveTopic.BENEFITS_LEGAL: (
        "Free independent benefits/debt advice: Citizens Advice — 0800 144 8848."
    ),
    SensitiveTopic.ABUSE: (
        "Support is available: National Domestic Abuse Helpline — 0808 2000 247 (24/7)."
    ),
}


@dataclass
class CrisisVerdict:
    """Outcome of a sensitive-topic check."""

    sensitive: bool
    topics: list[str] = field(default_factory=list)
    no_jokes: bool = False
    no_clickbait: bool = False
    source_required: bool = False
    approval_required: bool = False
    signposting: list[str] = field(default_factory=list)
    advisory: str = ""

    def as_dict(self) -> dict:
        return {
            "sensitive": self.sensitive,
            "topics": self.topics,
            "requirements": {
                "no_jokes": self.no_jokes,
                "no_clickbait": self.no_clickbait,
                "source_required": self.source_required,
                "approval_required": self.approval_required,
            },
            "signposting": self.signposting,
            "advisory": self.advisory,
        }


def detect_sensitive_topics(text: str) -> list[SensitiveTopic]:
    """Return the sensitive topics a piece of text touches (possibly empty)."""
    lowered = (text or "").lower()
    found: list[SensitiveTopic] = []
    for topic, markers in _TOPIC_MARKERS.items():
        if any(m in lowered for m in markers):
            found.append(topic)
    return found


def crisis_review(text: str) -> CrisisVerdict:
    """Decide whether ``text`` is sensitive and, if so, the care it demands.

    Non-sensitive content returns ``sensitive=False`` with no requirements. Sensitive
    content always requires human approval, bans jokes and clickbait, and carries the
    relevant UK signposting; suicide/self-harm, deterioration, hospital, discrimination
    and benefits/legal also require a credible source (they make factual/serious claims).
    """
    topics = detect_sensitive_topics(text)
    if not topics:
        return CrisisVerdict(sensitive=False, advisory="Not a sensitive topic.")

    signposts = [_SIGNPOSTS[t] for t in topics if t in _SIGNPOSTS]
    source_required = any(
        t in {
            SensitiveTopic.SUICIDE_SELF_HARM,
            SensitiveTopic.ILLNESS_DETERIORATION,
            SensitiveTopic.HOSPITAL,
            SensitiveTopic.DISABILITY_DISCRIMINATION,
            SensitiveTopic.BENEFITS_LEGAL,
        }
        for t in topics
    )
    return CrisisVerdict(
        sensitive=True,
        topics=[t.value for t in topics],
        no_jokes=True,
        no_clickbait=True,
        source_required=source_required,
        approval_required=True,
        signposting=signposts,
        advisory=(
            "Sensitive topic — crisis mode: no jokes, no clickbait, human approval "
            "required" + (", credible source required" if source_required else "")
            + ". Add the signposting where appropriate."
        ),
    )
