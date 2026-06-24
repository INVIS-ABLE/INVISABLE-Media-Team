"""The policy constants that the guardrail engine enforces.

These lists are transcribed directly from the platform directive. They live in one
place so the values are auditable and so every engine references the *same* source
of truth.
"""

from __future__ import annotations

# What the platform optimises for (drives the ScoreCard weights too).
OPTIMISE_FOR: tuple[str, ...] = (
    "trust",
    "awareness",
    "authenticity",
    "consistency",
    "education",
    "humour",
    "community value",
    "long-term brand building",
)

# What the platform must never optimise for.
NEVER_OPTIMISE_FOR: tuple[str, ...] = (
    "controversy",
    "outrage",
    "misinformation",
    "spam",
    "fake engagement",
    "fake stories",
    "fabricated testimonials",
    "fabricated founder experiences",
)

# Hard prohibitions on what the platform may produce or do.
NEVER_DO: tuple[str, ...] = (
    "copy copyrighted works",
    "duplicate creator content",
    "impersonate people without authorisation",
    "fabricate stories",
    "fabricate testimonials",
    "fabricate founder experiences",
)

# Emoji that must not appear in community engagement (hearts, kisses, flirtation).
# Commenting should be respectful, supportive and professional — not bait.
BANNED_EMOJI: tuple[str, ...] = (
    "❤",  # ❤ heart
    "\U0001f495",  # 💕 two hearts
    "\U0001f496",  # 💖 sparkling heart
    "\U0001f497",  # 💗 growing heart
    "\U0001f498",  # 💘 heart with arrow
    "\U0001f499",  # 💙
    "\U0001f49a",  # 💚
    "\U0001f49b",  # 💛
    "\U0001f49c",  # 💜
    "\U0001f49d",  # 💝
    "\U0001f48b",  # 💋 kiss mark
    "\U0001f618",  # 😘 face blowing a kiss
    "\U0001f617",  # 😗 kissing face
    "\U0001f619",  # 😙
    "\U0001f61a",  # 😚
    "\U0001f60d",  # 😍 heart-eyes
    "\U0001f970",  # 🥰 smiling with hearts
    "\U0001f60f",  # 😏 smirk (flirtatious)
    "\U0001f445",  # 👅 tongue
    "\U0001f346",  # 🍆
    "\U0001f351",  # 🍑
)

# Phrases that strongly signal low-effort engagement bait / spam comments.
ENGAGEMENT_BAIT_PHRASES: tuple[str, ...] = (
    "check out my",
    "follow for follow",
    "f4f",
    "dm me to make money",
    "link in bio to get rich",
    "comment below if you agree",
    "tag 3 friends",
    "first!",
    "great post!!!",
)

# Phrases that signal fabrication or invented experience. Used as a heuristic
# tripwire; the LLM-backed reviewer does the nuanced work, this catches the blatant.
FABRICATION_TRIPWIRES: tuple[str, ...] = (
    "this definitely happened",
    "true story i made up",
    "fake testimonial",
    "pretend i have",
    "act as if stephen suffered",
    "invent a founder story",
    "made-up customer review",
)

# Misinformation tripwires around medical claims — invisible-illness content must
# never overclaim. Cures, guarantees and absolutes are red flags.
MEDICAL_OVERCLAIM_TRIPWIRES: tuple[str, ...] = (
    "guaranteed cure",
    "cures your illness",
    "doctors hate this",
    "100% cure",
    "proven to cure",
    "miracle cure",
)

# ============================================================================
# Humour & Personality brand-safety
#
# INVISABLE® humour should never be sterile. The brand laughs *with* the
# community and at the founder's own experiences — never at vulnerable people.
# The rule: humour about your own experience, self-deprecation, shared
# frustration, trades banter, and situations is ALLOWED. Targeting people,
# disabilities, illnesses, or vulnerable groups is NOT. The goal is to make
# people laugh with us, not at others.
# ============================================================================

# First-person markers. Their presence makes a line self-referential / self-
# deprecating, which is allowed even when it jokes about illness or struggle.
FIRST_PERSON_MARKERS: tuple[str, ...] = (
    "i ",
    "i'm",
    "i've",
    "i'd",
    "im ",
    "my ",
    "me ",
    "myself",
    "we ",
    "we're",
    "us ",
    "our ",
    "mine",
)

# Slur / hate blocklist used SOLELY to block such content. Kept small and
# extensible (load more from an external moderation list in production). These
# are matched as whole words so ordinary text is never caught.
SLUR_BLOCKLIST: tuple[str, ...] = (
    "retard",
    "retarded",
    "spastic",
    "spaz",
    "cripple",
    "cripples",
    "psycho",  # when used as a slur for mental illness
    "nutter",
    "window licker",
)

# Derogatory frames that, when aimed at a group in the third person, constitute
# "punching down".
PUNCHING_DOWN_FRAMES: tuple[str, ...] = (
    "are lazy",
    "are just lazy",
    "are faking",
    "are fakers",
    "are scroungers",
    "are spongers",
    "are scumbags",
    "are pathetic",
    "are losers",
    "are a joke",
    "deserve it",
    "just want attention",
    "should be ashamed",
    "are a burden",
    "are worthless",
    "need to get over it",
)

# Group references that must not be the *target* of mockery (third person).
VULNERABLE_GROUP_TOKENS: tuple[str, ...] = (
    "disabled people",
    "sick people",
    "ill people",
    "chronically ill",
    "people with disabilities",
    "the disabled",
    "benefit claimants",
    "claimants",
    "immigrants",
    "the unemployed",
    "homeless people",
    "mental health patients",
)

# Harassment of a named individual — a directed insult at an @handle / name.
HARASSMENT_FRAMES: tuple[str, ...] = (
    "you're pathetic",
    "you are pathetic",
    "you're a joke",
    "you idiot",
    "you moron",
    "shut up you",
    "nobody likes you",
    "kill yourself",
    "kys",
)

# Swearing classifier. Swearing is allowed when it is natural, relatable, and
# British in register — and never when it targets a person or group (that is
# caught by the harassment / punching-down checks above).
SWEAR_WORDS_LIGHT: tuple[str, ...] = ("damn", "bloody", "crap", "bugger", "sod", "arse", "hell")
SWEAR_WORDS_MODERATE: tuple[str, ...] = ("shit", "piss", "bollocks", "pissed", "knobhead")
SWEAR_WORDS_STRONG: tuple[str, ...] = ("fuck", "fucking", "fucked", "wanker", "twat")

# ============================================================================
# Risk Scanner — advisory flags for high-stakes content that a human should
# review before publishing (never auto-blocked, but never auto-published either).
# ============================================================================
RISK_CATEGORIES: dict[str, tuple[str, ...]] = {
    "medical_advice": (
        "you should take",
        "stop taking your",
        "the right dose",
        "treat your",
        "diagnose",
        "you have",
    ),
    "benefits_advice": (
        "pip",
        "esa",
        "universal credit",
        "you will get",
        "you qualify for",
        "claim for",
        "tribunal",
    ),
    "legal_advice": (
        "you can sue",
        "your employer must",
        "it's illegal for",
        "you're entitled to",
        "unfair dismissal",
        "discrimination claim",
    ),
    "sponsor_claim": (
        "guarantees",
        "best on the market",
        "proven to",
        "outperforms",
        "number one",
    ),
    "copyright": (
        "official audio",
        "use this song",
        "movie clip",
        "tv clip",
        "copyrighted",
    ),
}

# The Prime Directive, verbatim, for display and logging.
PRIME_DIRECTIVE = (
    "If a decision increases reach but damages trust, reject it. "
    "If a decision increases awareness, trust, community value, and founder "
    "recognition simultaneously, prioritise it."
)
