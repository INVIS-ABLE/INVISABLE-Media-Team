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

# The Prime Directive, verbatim, for display and logging.
PRIME_DIRECTIVE = (
    "If a decision increases reach but damages trust, reject it. "
    "If a decision increases awareness, trust, community value, and founder "
    "recognition simultaneously, prioritise it."
)
