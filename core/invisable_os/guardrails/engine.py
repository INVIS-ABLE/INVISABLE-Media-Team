"""The guardrail engine — a deterministic hard gate.

Every candidate must pass :func:`check` before it can be scored for selection or
published. The check is intentionally deterministic and dependency-free so it is
fast, fully testable, and can never be "talked around" by a model. LLM-backed
review (nuanced fabrication / tone analysis) layers *on top* of this floor; it can
add violations but it can never remove one this gate has found.
"""

from __future__ import annotations

from invisable_os.guardrails.policy import (
    BANNED_EMOJI,
    ENGAGEMENT_BAIT_PHRASES,
    FABRICATION_TRIPWIRES,
    MEDICAL_OVERCLAIM_TRIPWIRES,
    PRIME_DIRECTIVE,
)
from invisable_os.models.content import ContentCandidate, ContentFormat
from invisable_os.models.scoring import GuardrailVerdict


def check(candidate: ContentCandidate) -> GuardrailVerdict:
    """Run the hard-gate checks against a candidate.

    Returns a :class:`GuardrailVerdict`. ``passed`` is ``False`` if *any* hard
    prohibition is tripped — in which case the candidate's selection score is
    forced to zero and it can never be published.
    """
    text = candidate.full_text
    lowered = text.lower()
    violations: list[str] = []
    notes: list[str] = []

    # 1. Originality must be asserted. Learning mechanics is fine; copying is not.
    if not candidate.original:
        violations.append("Candidate is not marked original — copying is prohibited.")

    # 2. Fabrication tripwires (stories, testimonials, founder experiences).
    for phrase in FABRICATION_TRIPWIRES:
        if phrase in lowered:
            violations.append(f"Fabrication signal detected: '{phrase}'.")

    # 3. Medical overclaim / misinformation tripwires.
    for phrase in MEDICAL_OVERCLAIM_TRIPWIRES:
        if phrase in lowered:
            violations.append(f"Medical overclaim / misinformation signal: '{phrase}'.")

    # 4. Engagement-bait / spam phrases.
    for phrase in ENGAGEMENT_BAIT_PHRASES:
        if phrase in lowered:
            violations.append(f"Engagement-bait / spam phrase: '{phrase}'.")

    # 5. Emoji policy — strictest on comments (community engagement), but banned
    #    flirtatious/heart/kiss emoji are never acceptable anywhere.
    banned_found = sorted({e for e in BANNED_EMOJI if e in text})
    if banned_found:
        violations.append(
            "Banned emoji present (hearts/kisses/flirtatious): "
            + " ".join(banned_found)
        )

    # 6. Comment-specific hygiene: keep engagement professional and low-emoji.
    if candidate.content_format == ContentFormat.COMMENT:
        emoji_count = _count_emoji(text)
        if emoji_count > 1:
            violations.append(
                f"Comment uses {emoji_count} emoji — community engagement must avoid "
                "excessive emoji use (max 1)."
            )
        if len(text) < 15:
            notes.append("Comment is very short — ensure it is genuinely constructive.")

    passed = len(violations) == 0
    if passed:
        notes.append("Passed all hard gates. Prime Directive: " + PRIME_DIRECTIVE)

    return GuardrailVerdict(passed=passed, violations=violations, notes=notes)


def explain(verdict: GuardrailVerdict) -> str:
    """Human-readable summary of a verdict, for logs and review surfaces."""
    if verdict.passed:
        return "PASS — candidate cleared all hard gates."
    lines = ["BLOCK — candidate failed the guardrails:"]
    lines.extend(f"  - {v}" for v in verdict.violations)
    return "\n".join(lines)


# --- emoji counting ---------------------------------------------------------

# Unicode ranges that cover the bulk of pictographic emoji. Kept local and simple;
# the goal is a robust heuristic, not a full Unicode segmentation engine.
_EMOJI_RANGES: tuple[tuple[int, int], ...] = (
    (0x1F300, 0x1FAFF),  # symbols & pictographs, supplemental, extended-A
    (0x2600, 0x27BF),  # misc symbols & dingbats
    (0x1F1E6, 0x1F1FF),  # regional indicators (flags)
    (0x2190, 0x21FF),  # arrows
    (0xFE00, 0xFE0F),  # variation selectors
)


def _count_emoji(text: str) -> int:
    count = 0
    for ch in text:
        code = ord(ch)
        if any(lo <= code <= hi for lo, hi in _EMOJI_RANGES):
            count += 1
    return count
