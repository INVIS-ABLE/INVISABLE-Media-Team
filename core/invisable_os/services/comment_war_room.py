"""Comment War Room — triage incoming comments and draft safe replies.

A busy post can draw hundreds of comments: warm support, genuine questions, the
odd troll, spam, and — sometimes — someone quietly reaching out in crisis. The War
Room sorts the noise so the most important comments rise to the top:

* it classifies each comment (crisis · question · support · lead · abuse · spam · neutral),
* prioritises them (a crisis or a partnership lead beats a "nice one"),
* decides an action (reply · escalate · do-not-engage · ignore), and
* drafts a guardrail-safe reply where one is warranted — never for a troll, never
  an auto-reply to someone in crisis (that's escalated to a human with signposting).

Detection is deterministic phrase-matching and reuse of [Crisis Mode]; reply
drafts are vetted by the same brand guardrails the rest of the platform uses.
Everything runs offline.
"""

from __future__ import annotations

from invisable_os.guardrails import check
from invisable_os.guardrails.crisis import crisis_review
from invisable_os.models.content import ContentCandidate, ContentFormat, Platform

# Categories, in the order we test for them (first match wins). Crisis always
# trumps everything; abuse/spam are filtered before we'd ever reply.
CATEGORIES = ("crisis", "abuse", "spam", "lead", "question", "support", "neutral")

# Lower number = handled sooner. A crisis or a lead must not sit behind small talk.
_PRIORITY = {
    "crisis": 1,
    "lead": 2,
    "question": 3,
    "support": 4,
    "neutral": 5,
    "abuse": 6,
    "spam": 7,
}

# What to do with each category.
_ACTION = {
    "crisis": "escalate",        # to a human, with signposting attached
    "lead": "escalate",          # to the founder / partnerships
    "question": "reply",
    "support": "reply",
    "neutral": "reply",
    "abuse": "do_not_engage",
    "spam": "ignore",
}

_ABUSE = (
    "idiot", "stupid", "scam", "fraud", "fake", "shut up", "hate you", "loser",
    "pathetic", "grifter", "clown", "nonsense", "rubbish account",
)
_SPAM = (
    "http://", "https://", "www.", ".com", "dm me", "check my", "check out my",
    "free followers", "buy now", "click here", "promo", "earn money", "crypto",
)
_LEAD = (
    "sponsor", "sponsorship", "partnership", "collaborate", "collab", "work together",
    "wholesale", "stockist", "invoice", "quote for", "business enquiry", "press enquiry",
    "media enquiry", "interview you",
)
_SUPPORT = (
    "thank", "thanks", "love this", "love that", "amazing", "needed this", "spot on",
    "well said", "this helped", "brave", "so true", "respect", "legend", "appreciate",
)
_QUESTION_WORDS = (
    "how ", "what ", "where ", "when ", "why ", "who ", "can ", "could ", "does ",
    "do you", "is there", "are there", "should ", "would ",
)

# Deterministic, guardrail-clean reply templates per repliable category.
_REPLIES = {
    "question": (
        "Great question — happy to help. Drop us a DM with a few details and we'll "
        "point you in the right direction."
    ),
    "support": (
        "Thank you, that genuinely means a lot. You're not invisible here — glad this "
        "landed with you."
    ),
    "neutral": (
        "Appreciate you taking the time to comment — thanks for being here and being "
        "part of this."
    ),
}


def _classify(text: str, sensitive: bool) -> str:
    if sensitive:
        return "crisis"
    low = text.lower()
    if any(w in low for w in _ABUSE):
        return "abuse"
    if any(w in low for w in _SPAM):
        return "spam"
    if any(w in low for w in _LEAD):
        return "lead"
    if "?" in text or any(low.startswith(w) or f" {w}" in low for w in _QUESTION_WORDS):
        return "question"
    if any(w in low for w in _SUPPORT):
        return "support"
    return "neutral"


def _vet_reply(text: str, platform: Platform) -> bool:
    """Run a drafted reply through the brand guardrails before we'd ever post it."""
    candidate = ContentCandidate(
        brief="comment reply",
        platform=platform,
        content_format=ContentFormat.COMMENT,
        body=text,
        original=True,
    )
    return check(candidate).passed


def triage_comment(text: str, *, platform: Platform = Platform.INSTAGRAM) -> dict:
    """Classify one comment and produce its action + (where warranted) a safe reply."""
    text = (text or "").strip()
    verdict = crisis_review(text)
    category = _classify(text, verdict.sensitive)
    action = _ACTION[category]

    reply: str | None = None
    reply_approved: bool | None = None
    if action == "reply":
        draft = _REPLIES[category]
        if _vet_reply(draft, platform):
            reply, reply_approved = draft, True
        else:
            reply_approved = False  # template failed the gate — withhold it

    return {
        "text": text,
        "category": category,
        "priority": _PRIORITY[category],
        "action": action,
        "reply": reply,
        "reply_approved": reply_approved,
        "sensitive": verdict.sensitive,
        "topics": list(verdict.topics) if verdict.sensitive else [],
        "signposting": list(verdict.signposting) if verdict.sensitive else [],
    }


def triage_comments(comments, *, platform: Platform = Platform.INSTAGRAM) -> dict:
    """Triage a batch of comments, sorted with the most important first.

    ``comments`` may be a list of strings or of dicts with a ``text`` field.
    """
    items: list[dict] = []
    for c in comments or []:
        text = c.get("text", "") if isinstance(c, dict) else c
        items.append(triage_comment(text, platform=platform))

    items.sort(key=lambda r: r["priority"])

    by_category: dict[str, int] = {}
    by_action: dict[str, int] = {}
    for it in items:
        by_category[it["category"]] = by_category.get(it["category"], 0) + 1
        by_action[it["action"]] = by_action.get(it["action"], 0) + 1

    return {
        "total": len(items),
        "by_category": by_category,
        "by_action": by_action,
        "escalations": by_action.get("escalate", 0),
        "comments": items,
    }
