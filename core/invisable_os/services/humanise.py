"""Humanisation layer — strip the AI tells so copy reads like a person wrote it.

Generated copy has a tell: stock clichés ("delve", "game-changer", "in today's
fast-paced world"), throat-clearing ("it's important to note that"), connective
scaffolding ("Furthermore,", "In conclusion,"), em-dash overuse, and emoji spam.
None of it sounds like a tradesperson talking straight.

This layer does two things, deterministically and offline:

* ``humanness_score`` flags the tells and scores how human the copy reads (0–1);
* ``humanise`` returns a cleaned version with the tells removed or plainened, plus
  the score before and after — so the approval UI (or any caller) can run a draft
  through it before it goes near the queue.

It never changes meaning beyond swapping inflated words for plain ones; it's a
polish pass, not a rewrite.
"""

from __future__ import annotations

import re

# Inflated phrase → plain replacement. Order matters (longer phrases first so a
# multi-word cliché is caught before its substrings). Empty string = delete it.
_REPLACEMENTS: list[tuple[str, str]] = [
    (r"in today'?s fast-paced world,?\s*", ""),
    (r"it'?s important to note that\s*", ""),
    (r"it'?s worth noting that\s*", ""),
    (r"when it comes to\b", "with"),
    (r"embark on a journey\b", "start"),
    (r"unlock the power of\b", "use"),
    (r"harness the power of\b", "use"),
    (r"in the realm of\b", "in"),
    (r"look no further\b", ""),
    (r"a testament to\b", "proof of"),
    (r"testament to\b", "shows"),
    (r"ever-evolving\b", "changing"),
    (r"game-?changer\b", "big deal"),
    (r"cutting-edge\b", "modern"),
    (r"elevate your\b", "improve your"),
    (r"navigate the\b", "handle the"),
    (r"delve into\b", "look at"),
    (r"dive into\b", "get into"),
    (r"\bdelve\b", "look"),
    (r"\bleverage\b", "use"),
    (r"\butili[sz]e\b", "use"),
    (r"\bseamless\b", "smooth"),
    (r"\brobust\b", "solid"),
    (r"\bfurthermore,?\s*", "also "),
    (r"\bmoreover,?\s*", "also "),
    (r"\bin conclusion,?\s*", ""),
]

# Structural / lexical tells we flag (and, where listed above, clean).
_CLICHE_PATTERNS = [re.compile(p, re.IGNORECASE) for p, _ in _REPLACEMENTS]

# A broad emoji range — enough to catch spammed faces/hearts/hands.
_EMOJI = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff]"
)
_LADDER = re.compile(r"\b(firstly|secondly|thirdly|lastly)\b", re.IGNORECASE)
_NOT_ONLY = re.compile(r"\bnot only\b.*?\bbut also\b", re.IGNORECASE)

_EMOJI_LIMIT = 3
_EMDASH_LIMIT = 2
_PENALTY = 0.12


def _find_tells(text: str) -> list[dict]:
    tells: list[dict] = []
    for pat in _CLICHE_PATTERNS:
        for m in pat.finditer(text):
            tells.append({"kind": "cliche", "match": m.group(0).strip()})
    emoji = _EMOJI.findall(text)
    if len(emoji) > _EMOJI_LIMIT:
        tells.append({"kind": "emoji_spam", "match": f"{len(emoji)} emoji"})
    emdashes = text.count("—") + text.count(" - ")
    if emdashes > _EMDASH_LIMIT:
        tells.append({"kind": "em_dash_overuse", "match": f"{emdashes} dashes"})
    if _LADDER.search(text):
        tells.append({"kind": "ladder", "match": "firstly/secondly/lastly"})
    if _NOT_ONLY.search(text):
        tells.append({"kind": "not_only_but_also", "match": "not only… but also"})
    return tells


def _score(tells: list[dict]) -> float:
    return round(max(0.0, 1.0 - _PENALTY * len(tells)), 3)


def humanness_score(text: str) -> dict:
    """Flag the AI tells in ``text`` and score how human it reads (0–1)."""
    tells = _find_tells(text or "")
    by_kind: dict[str, int] = {}
    for t in tells:
        by_kind[t["kind"]] = by_kind.get(t["kind"], 0) + 1
    return {
        "score": _score(tells),
        "human": _score(tells) >= 0.8,
        "tell_count": len(tells),
        "by_kind": by_kind,
        "tells": tells,
    }


def _tidy(text: str) -> str:
    """Collapse the whitespace/punctuation artefacts left by deletions."""
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"^[\s,;:]+", "", text)
    # Re-capitalise the first letter of each sentence after a clean-up.
    def _cap(m: re.Match) -> str:
        return m.group(1) + m.group(2).upper()
    text = re.sub(r"(^|[.!?]\s+)([a-z])", _cap, text)
    return text.strip()


def humanise(text: str) -> dict:
    """Return a de-AI'd version of ``text`` with the score before and after."""
    original = text or ""
    before = humanness_score(original)

    cleaned = original
    for pattern, repl in _REPLACEMENTS:
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
    # Normalise em-dashes to plain commas/spacing; the score already noted overuse.
    cleaned = cleaned.replace(" — ", ", ").replace("—", ", ")
    cleaned = _tidy(cleaned)

    after = humanness_score(cleaned)
    return {
        "original": original,
        "humanised": cleaned,
        "score_before": before["score"],
        "score_after": after["score"],
        "removed": before["tell_count"] - after["tell_count"],
        "tells_before": before["tells"],
        "remaining_tells": after["tells"],
    }
