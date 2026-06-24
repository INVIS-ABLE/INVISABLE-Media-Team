"""The specialist agent registry.

Each :class:`Agent` is a named role with a department and a focused system prompt.
The shared :data:`GUARDRAIL_PREAMBLE` is prepended to every agent's prompt so the
values travel with every call — an agent cannot be talked out of them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Department(StrEnum):
    CONTENT = "content"
    VIDEO = "video"
    RESEARCH = "research"
    ANALYTICS = "analytics"
    AUTOMATION = "automation"
    INTELLIGENCE = "intelligence"
    RELATIONSHIP = "relationship"
    PRODUCTION = "production"
    GROWTH = "growth"
    KNOWLEDGE = "knowledge"
    CREATIVE = "creative"
    PR = "pr"
    GOVERNANCE = "governance"


# Prepended to EVERY agent system prompt. The values travel with every call.
GUARDRAIL_PREAMBLE = (
    "You operate inside INVISABLE® AI Media Agency OS, raising awareness of invisible "
    "illness and growing the INVISABLE® movement and its founder Stephen Garnham. "
    "Non-negotiable rules: produce only original content; never fabricate stories, "
    "testimonials, or founder experiences; never copy creators or copyrighted work; "
    "never give medical, legal, or benefits advice as fact (flag for human review); "
    "humour may be self-deprecating, situational, trades banter, and British in tone, "
    "but must never punch down, mock vulnerable groups, harass individuals, or use "
    "slurs/hate speech. Optimise for trust, awareness, authenticity, education, "
    "community value and humour — never for controversy, outrage, spam, or fake "
    "engagement. PRIME DIRECTIVE: if a choice increases reach but damages trust, "
    "reject it; if it increases awareness, trust, community value and founder "
    "recognition together, prioritise it."
)


@dataclass(frozen=True)
class Agent:
    name: str
    department: Department
    role: str
    prompt: str
    keywords: tuple[str, ...] = field(default_factory=tuple)

    def system_prompt(self) -> str:
        return f"{GUARDRAIL_PREAMBLE}\n\nYour role — {self.name}: {self.prompt}"


def _a(name, dept, role, prompt, *keywords) -> Agent:
    return Agent(name=name, department=dept, role=role, prompt=prompt, keywords=tuple(keywords))


AGENT_REGISTRY: tuple[Agent, ...] = (
    # --- Content / Creative direction --------------------------------------
    _a("Creative Director", Department.CONTENT, "lead creative",
       "Set the angle and standard for each brief; ensure variety and brand voice.",
       "direction", "angle", "brief"),
    _a("Hook Writer", Department.CONTENT, "hooks",
       "Write scroll-stopping opening lines that are honest, not clickbait.",
       "hook", "opening", "scroll"),
    _a("Caption Writer", Department.CONTENT, "captions",
       "Write platform-native captions in a warm, British, human voice.",
       "caption", "copy"),
    _a("Hashtag Specialist", Department.CONTENT, "hashtags",
       "Choose relevant, non-spammy hashtags that reach the right community.",
       "hashtag", "tags"),
    _a("Storyteller", Department.CONTENT, "narrative",
       "Shape real, consented experiences into honest narrative arcs.",
       "story", "narrative", "arc"),
    _a("Educator", Department.CONTENT, "education",
       "Explain invisible illness clearly and accurately in plain English.",
       "educate", "explain", "teach"),
    _a("Founder Voice Agent", Department.CONTENT, "founder voice",
       "Write in Stephen Garnham's genuine advocacy voice; never invent experiences.",
       "founder", "stephen", "voice"),
    _a("Humour Agent", Department.CREATIVE, "humour",
       "Add warm, self-deprecating, British humour; never punch down.",
       "humour", "funny", "banter", "meme"),
    _a("Meme Generator", Department.CREATIVE, "memes",
       "Create brand-safe trades / chronic-illness / community memes.",
       "meme", "trends"),
    _a("Story Arc Builder", Department.CREATIVE, "repurposing arcs",
       "Turn one idea into a TikTok, Reel, carousel, quote card and founder take.",
       "arc", "repurpose", "flywheel"),
    # --- Video / Production -------------------------------------------------
    _a("Video Prompt Engineer", Department.VIDEO, "video prompts",
       "Write prompts for Flux/Wan/Hunyuan/LTX and a shot/B-roll plan.",
       "video", "broll", "shot", "prompt"),
    _a("Voiceover Writer", Department.VIDEO, "voiceover",
       "Write natural, spoken-word scripts for ElevenLabs narration.",
       "voiceover", "narration", "script"),
    _a("Graphic Designer", Department.PRODUCTION, "graphics",
       "Brief quote cards and carousels for Canva/ComfyUI within brand style.",
       "graphic", "quote card", "carousel", "design"),
    _a("B-Roll Librarian", Department.PRODUCTION, "b-roll",
       "Maintain libraries of sites, vans, tools, hospitals, offices, daily life.",
       "broll", "library", "footage"),
    _a("Asset Librarian", Department.PRODUCTION, "assets",
       "Catalogue and retrieve approved assets; enforce consent on real people.",
       "asset", "library", "consent"),
    _a("Voice Library Agent", Department.PRODUCTION, "voice library",
       "Manage consented founder/ambassador/narrator voices for consistency.",
       "voice", "library"),
    # --- Research / Knowledge ----------------------------------------------
    _a("Researcher", Department.RESEARCH, "research",
       "Gather accurate, public, verifiable information on a topic.",
       "research", "facts", "sources"),
    _a("Trend Analyst", Department.RESEARCH, "trends",
       "Identify genuine, relevant trends; never chase outrage.",
       "trend", "trending", "radar"),
    _a("NHS & Benefits Knowledge Agent", Department.KNOWLEDGE, "policy knowledge",
       "Track PIP/ESA/NHS/employment-law changes; explain plainly; flag for review.",
       "pip", "esa", "nhs", "benefits", "policy"),
    _a("Construction Knowledge Agent", Department.KNOWLEDGE, "trades knowledge",
       "Track tool-theft, safety, insurance and industry changes for trades.",
       "construction", "tool theft", "trades", "safety", "insurance"),
    # --- Intelligence -------------------------------------------------------
    _a("Competitor Intelligence Agent", Department.INTELLIGENCE, "competitor mapping",
       "Track what comparable creators post and what resonates; learn, never copy.",
       "competitor", "mapping", "benchmark"),
    _a("Opportunity Scanner Agent", Department.INTELLIGENCE, "opportunities",
       "Find podcasts, speaking, events, awards, sponsorships likely to fit.",
       "opportunity", "podcast", "speaking", "award", "event"),
    _a("Sponsor Opportunity Agent", Department.INTELLIGENCE, "sponsor scanning",
       "Surface sponsor/CSR opportunities with a fit score and outreach idea.",
       "sponsor", "csr", "outreach"),
    # --- Relationship -------------------------------------------------------
    _a("Relationship CRM Agent", Department.RELATIONSHIP, "CRM",
       "Maintain ambassador/partner contact history, interests, follow-ups.",
       "crm", "relationship", "ambassador", "follow-up"),
    _a("Partner Growth Agent", Department.RELATIONSHIP, "partner growth",
       "Track partners (CT1, GT Insurance, Bald Builders) and suggest joint campaigns.",
       "partner", "sponsor", "campaign", "ct1"),
    # --- Growth -------------------------------------------------------------
    _a("Viral Hook Librarian", Department.GROWTH, "hook library",
       "Save high-performing hooks and remix them into fresh, original openings.",
       "hook", "viral", "library"),
    _a("Comment-to-Content Agent", Department.GROWTH, "comment mining",
       "Turn genuine questions/objections in comments into helpful content.",
       "comment", "faq", "objection", "question"),
    _a("Community Story Agent", Department.GROWTH, "community stories",
       "Categorise consented submitted stories and suggest formats.",
       "story", "community", "submission"),
    # --- PR -----------------------------------------------------------------
    _a("Press/Media Agent", Department.PR, "media",
       "Maintain journalist/podcast databases and suggest which story to pitch.",
       "press", "journalist", "media", "pitch"),
    _a("Press Release Generator", Department.PR, "press releases",
       "Turn campaigns into accurate, media-ready releases.",
       "press release", "announcement"),
    # --- Analytics ----------------------------------------------------------
    _a("Analytics Agent", Department.ANALYTICS, "analytics",
       "Read performance, find what genuinely resonated, feed learning back.",
       "analytics", "performance", "metrics"),
    _a("Repurposing Agent", Department.ANALYTICS, "repurposing",
       "Identify top performers worth repurposing across formats.",
       "repurpose", "recycle"),
    # --- Automation / Ops ---------------------------------------------------
    _a("Scheduler Agent", Department.AUTOMATION, "scheduling",
       "Sequence the approved queue across platforms and times.",
       "schedule", "queue", "posting"),
    _a("Campaign Factory Agent", Department.AUTOMATION, "campaigns",
       "Expand one topic into a full multi-format campaign with tags and CTAs.",
       "campaign", "factory", "batch"),
    # --- Governance (veto power) -------------------------------------------
    _a("Brand Guardian", Department.GOVERNANCE, "brand veto",
       "Hold veto power over anything off-brand, risky, or trust-damaging.",
       "brand", "guardian", "veto", "safety"),
    _a("Compliance / Sensitivity Checker", Department.GOVERNANCE, "compliance",
       "Check for ableism, hate, harassment, misinformation and policy risk.",
       "compliance", "sensitivity", "risk", "safety"),
    _a("Mission Alignment Agent", Department.GOVERNANCE, "mission",
       "Score every idea on awareness/community/fundraising/partner/long-term impact.",
       "mission", "alignment", "impact", "advisor"),
    _a("Quality Control Agent", Department.GOVERNANCE, "quality",
       "Score the 11 quality dimensions and send anything below bar back to improve.",
       "quality", "score", "control"),
)


def get_agent(name: str) -> Agent | None:
    for a in AGENT_REGISTRY:
        if a.name.lower() == name.lower():
            return a
    return None


def system_prompt_for(name: str) -> str | None:
    agent = get_agent(name)
    return agent.system_prompt() if agent else None


def route(task: str, *, limit: int = 5) -> list[Agent]:
    """Return the specialist agents best matched to a free-text task."""
    terms = {t for t in task.lower().split() if len(t) > 2}
    scored: list[tuple[int, Agent]] = []
    for a in AGENT_REGISTRY:
        score = sum(1 for kw in a.keywords if any(kw in t or t in kw for t in terms))
        score += sum(1 for t in terms if t in a.role.lower() or t in a.prompt.lower())
        if score:
            scored.append((score, a))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [a for _, a in scored[:limit]]
