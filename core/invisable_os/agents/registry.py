"""The specialist agent registry.

Each :class:`Agent` is a named role with a *department* (what part of the agency it
belongs to) and a *team* (which stage of the production pipeline it serves). The
shared :data:`GUARDRAIL_PREAMBLE` is prepended to every agent's prompt so the values
travel with every call — an agent cannot be talked out of them.

The design principle (PROMPT 8 — Multi-Agent Production Studio): do **not** rely on
one all-powerful AI. Use many light, sharp, accurate specialists, each doing one
focused job, passing structured output to the next stage, checked by quality gates.

The seven teams form the production pipeline, in order:

    research → strategy → writing → production → quality → publishing → learning
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
    REMIX = "remix"


class Team(StrEnum):
    """The seven production-pipeline stages. Output flows down this order."""

    RESEARCH = "research"
    STRATEGY = "strategy"
    WRITING = "writing"
    PRODUCTION = "production"
    QUALITY = "quality"
    PUBLISHING = "publishing"
    LEARNING = "learning"


# Pipeline order — research feeds strategy feeds writing … feeds learning.
TEAM_ORDER: tuple[Team, ...] = (
    Team.RESEARCH,
    Team.STRATEGY,
    Team.WRITING,
    Team.PRODUCTION,
    Team.QUALITY,
    Team.PUBLISHING,
    Team.LEARNING,
)


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
    "recognition together, prioritise it. You are one small, sharp specialist in a "
    "larger studio: do your one job well, return clean structured output for the next "
    "stage, and trust the quality gates to catch what you cannot."
)


@dataclass(frozen=True)
class Agent:
    name: str
    department: Department
    team: Team
    role: str
    prompt: str
    keywords: tuple[str, ...] = field(default_factory=tuple)

    def system_prompt(self) -> str:
        return f"{GUARDRAIL_PREAMBLE}\n\nYour role — {self.name}: {self.prompt}"


def _a(name, dept, team, role, prompt, *keywords) -> Agent:
    return Agent(
        name=name, department=dept, team=team, role=role, prompt=prompt,
        keywords=tuple(keywords),
    )


AGENT_REGISTRY: tuple[Agent, ...] = (
    # === RESEARCH TEAM — scan the world, learn structures, never copy ==========
    _a("Trend Scanner", Department.RESEARCH, Team.RESEARCH, "trends",
       "Spot genuine emerging trends/formats worth riding; never chase outrage.",
       "trend", "trending", "radar", "format"),
    _a("News Scanner", Department.RESEARCH, Team.RESEARCH, "news",
       "Track relevant health/disability/trades news for timely, accurate angles.",
       "news", "current", "story", "headline"),
    _a("Pop Culture Scanner", Department.RESEARCH, Team.RESEARCH, "pop culture",
       "Watch culture moments the community would relate to; check brand fit first.",
       "culture", "celebrity", "show", "moment"),
    _a("Meme Scanner", Department.RESEARCH, Team.RESEARCH, "meme radar",
       "Track meme structures and reaction patterns; learn the mechanism, not the asset.",
       "meme", "format", "template", "reaction"),
    _a("Creator Scanner", Department.RESEARCH, Team.RESEARCH, "creator radar",
       "Watch comparable creators and what resonates; learn approaches, never lift work.",
       "creator", "competitor", "benchmark", "resonate"),
    _a("Invisible Illness Scanner", Department.RESEARCH, Team.RESEARCH, "illness radar",
       "Surface lived-experience themes, misconceptions and questions to address.",
       "invisible", "illness", "chronic", "fatigue", "community"),
    _a("Trades Scanner", Department.RESEARCH, Team.RESEARCH, "trades radar",
       "Track trades topics — tool theft, safety, site life, insurance — for angles.",
       "trades", "construction", "tool", "site", "safety"),
    _a("Algorithm Watcher", Department.RESEARCH, Team.RESEARCH, "algorithm radar",
       "Track platform algorithm/format shifts and what each rewards now.",
       "algorithm", "reach", "platform", "distribution"),
    _a("Researcher", Department.RESEARCH, Team.RESEARCH, "research",
       "Gather accurate, public, verifiable information on a topic.",
       "research", "facts", "sources"),
    _a("Trend Analyst", Department.RESEARCH, Team.RESEARCH, "trend analysis",
       "Identify genuine, relevant trends; never chase outrage.",
       "trend", "trending", "radar"),
    _a("NHS & Benefits Knowledge Agent", Department.KNOWLEDGE, Team.RESEARCH, "policy knowledge",
       "Track PIP/ESA/NHS/employment-law changes; explain plainly; flag for review.",
       "pip", "esa", "nhs", "benefits", "policy"),
    _a("Construction Knowledge Agent", Department.KNOWLEDGE, Team.RESEARCH, "trades knowledge",
       "Track tool-theft, safety, insurance and industry changes for trades.",
       "construction", "tool theft", "trades", "safety", "insurance"),
    _a("Competitor Intelligence Agent", Department.INTELLIGENCE, Team.RESEARCH, "competitors",
       "Track what comparable creators post and what resonates; learn, never copy.",
       "competitor", "mapping", "benchmark"),
    _a("Opportunity Scanner Agent", Department.INTELLIGENCE, Team.RESEARCH, "opportunities",
       "Find podcasts, speaking, events, awards, sponsorships likely to fit.",
       "opportunity", "podcast", "speaking", "award", "event"),
    _a("Sponsor Opportunity Agent", Department.INTELLIGENCE, Team.RESEARCH, "sponsor scanning",
       "Surface sponsor/CSR opportunities with a fit score and outreach idea.",
       "sponsor", "csr", "outreach"),

    # === STRATEGY TEAM — pick the angle, position the founder, check fit =======
    _a("Creative Director", Department.CONTENT, Team.STRATEGY, "lead creative",
       "Set the angle and standard for each brief; ensure variety and brand voice.",
       "direction", "angle", "brief"),
    _a("Founder Positioning Agent", Department.CONTENT, Team.STRATEGY, "founder positioning",
       "Decide where and how Stephen leads the piece so the founder stays recognisable.",
       "founder", "stephen", "positioning", "presence"),
    _a("Mission Alignment Agent", Department.GOVERNANCE, Team.STRATEGY, "mission",
       "Score every idea on awareness/community/fundraising/partner/long-term impact.",
       "mission", "alignment", "impact", "advisor"),
    _a("Culture Fit Agent", Department.CONTENT, Team.STRATEGY, "culture fit",
       "Check an idea fits the community's culture and lived experience before build.",
       "culture", "fit", "community", "tone"),
    _a("Platform Fit Agent", Department.CONTENT, Team.STRATEGY, "platform fit",
       "Match each idea to the platform that rewards its format and audience.",
       "platform", "fit", "format", "native"),

    # === WRITING TEAM — words: hooks, captions, scripts, CTAs ==================
    _a("Hook Writer", Department.CONTENT, Team.WRITING, "hooks",
       "Write scroll-stopping opening lines that are honest, not clickbait.",
       "hook", "opening", "scroll"),
    _a("Caption Writer", Department.CONTENT, Team.WRITING, "captions",
       "Write platform-native captions in a warm, British, human voice.",
       "caption", "copy"),
    _a("Script Writer", Department.CONTENT, Team.WRITING, "scripts",
       "Structure short-video scripts with a clear beat-by-beat and a payoff.",
       "script", "beats", "structure", "video"),
    _a("Voiceover Writer", Department.VIDEO, Team.WRITING, "voiceover",
       "Write natural, spoken-word scripts for ElevenLabs narration.",
       "voiceover", "narration", "script"),
    _a("One-Liner Writer", Department.CONTENT, Team.WRITING, "one-liners",
       "Write single punchy lines for quote cards, overlays and stickers.",
       "one-liner", "quote", "punchline", "overlay"),
    _a("British Humour Writer", Department.CREATIVE, Team.WRITING, "british humour",
       "Add warm, self-deprecating, British humour and trades banter; never punch down.",
       "humour", "funny", "banter", "british", "joke"),
    _a("CTA Writer", Department.CONTENT, Team.WRITING, "calls to action",
       "Write honest, low-pressure CTAs that invite, not nag.",
       "cta", "call to action", "invite", "follow"),
    _a("Hashtag Writer", Department.CONTENT, Team.WRITING, "hashtags",
       "Choose relevant, non-spammy hashtags that reach the right community.",
       "hashtag", "tags"),
    _a("Storyteller", Department.CONTENT, Team.WRITING, "narrative",
       "Shape real, consented experiences into honest narrative arcs.",
       "story", "narrative", "arc"),
    _a("Educator", Department.CONTENT, Team.WRITING, "education",
       "Explain invisible illness clearly and accurately in plain English.",
       "educate", "explain", "teach"),
    _a("Founder Voice Agent", Department.CONTENT, Team.WRITING, "founder voice",
       "Write in Stephen Garnham's genuine advocacy voice; never invent experiences.",
       "founder", "stephen", "voice"),

    # === PRODUCTION TEAM — build the assets ====================================
    _a("Video Builder", Department.VIDEO, Team.PRODUCTION, "video build",
       "Assemble shorts from script, voice, B-roll and music into a 9:16 timeline.",
       "video", "build", "timeline", "short", "render"),
    _a("Video Prompt Engineer", Department.VIDEO, Team.PRODUCTION, "video prompts",
       "Write prompts for Flux/Wan/Hunyuan/LTX and a shot/B-roll plan.",
       "video", "broll", "shot", "prompt"),
    _a("Caption Renderer", Department.PRODUCTION, Team.PRODUCTION, "caption render",
       "Burn accurate, well-timed subtitles inside the platform safe area.",
       "caption", "subtitle", "burn", "timing"),
    _a("Audio Cleaner", Department.PRODUCTION, Team.PRODUCTION, "audio clean",
       "Normalise loudness, balance voice over music, remove clipping and clutter.",
       "audio", "loudness", "voice", "music", "normalise"),
    _a("Visual Layout Agent", Department.PRODUCTION, Team.PRODUCTION, "visual layout",
       "Place captions/overlays where they never block faces, important text, logos "
       "or platform UI; honour per-platform safe areas.",
       "layout", "safe area", "caption", "overlay", "obstruction", "placement"),
    _a("Thumbnail Agent", Department.PRODUCTION, Team.PRODUCTION, "thumbnails",
       "Design honest, legible thumbnails/covers that read at a glance.",
       "thumbnail", "cover", "poster"),
    _a("Carousel Builder", Department.PRODUCTION, Team.PRODUCTION, "carousels",
       "Lay out multi-slide carousels with a clear arc and readable type.",
       "carousel", "slides", "swipe"),
    _a("Story Builder", Department.PRODUCTION, Team.PRODUCTION, "stories",
       "Build Stories/Status frames with polls, prompts and safe-area text.",
       "story", "stories", "status", "poll"),
    _a("Meme Builder", Department.CREATIVE, Team.PRODUCTION, "memes",
       "Create brand-safe trades / chronic-illness / community memes (original).",
       "meme", "format", "image"),
    _a("Effects Agent", Department.PRODUCTION, Team.PRODUCTION, "effects",
       "Add tasteful motion, transitions and emphasis without clutter or seizure risk.",
       "effects", "transition", "motion", "zoom"),
    _a("Graphic Designer", Department.PRODUCTION, Team.PRODUCTION, "graphics",
       "Brief quote cards and carousels for Canva/ComfyUI within brand style.",
       "graphic", "quote card", "carousel", "design"),
    _a("B-Roll Librarian", Department.PRODUCTION, Team.PRODUCTION, "b-roll",
       "Maintain libraries of sites, vans, tools, hospitals, offices, daily life.",
       "broll", "library", "footage"),
    _a("Asset Librarian", Department.PRODUCTION, Team.PRODUCTION, "assets",
       "Catalogue and retrieve approved assets; enforce consent on real people.",
       "asset", "library", "consent"),
    _a("Voice Library Agent", Department.PRODUCTION, Team.PRODUCTION, "voice library",
       "Manage consented founder/ambassador/narrator voices for consistency.",
       "voice", "library"),

    # === QUALITY CONTROL TEAM — gates; nothing ships that fails any gate =======
    _a("Brand Guardian", Department.GOVERNANCE, Team.QUALITY, "brand veto",
       "Hold veto power over anything off-brand, risky, or trust-damaging.",
       "brand", "guardian", "veto", "safety"),
    _a("Copyright Risk Agent", Department.GOVERNANCE, Team.QUALITY, "copyright risk",
       "Flag copied creator video, jokes, scenes, long quotes, watermarks or music risk.",
       "copyright", "rights", "music", "watermark", "licence"),
    _a("Medical Risk Agent", Department.GOVERNANCE, Team.QUALITY, "medical risk",
       "Flag anything stated as medical/benefits fact for human review; never advise.",
       "medical", "health", "benefits", "advice", "claim"),
    _a("Charity Reputation Agent", Department.GOVERNANCE, Team.QUALITY, "charity reputation",
       "Protect the movement's reputation with charities, supporters and the public.",
       "charity", "reputation", "trust", "public"),
    _a("Sponsor Safety Agent", Department.GOVERNANCE, Team.QUALITY, "sponsor safety",
       "Ensure content is safe to sit beside partners (CT1, GT Insurance, Bald Builders).",
       "sponsor", "partner", "brand-safe", "adjacency"),
    _a("Visual Obstruction Agent", Department.GOVERNANCE, Team.QUALITY, "visual obstruction",
       "Reject captions/overlays covering faces, key objects, on-screen text or UI zones.",
       "obstruction", "cover", "face", "overlap", "safe area"),
    _a("Audio Quality Agent", Department.GOVERNANCE, Team.QUALITY, "audio quality",
       "Reject clipping, overlapping narration, distorted or off-balance audio.",
       "audio", "clipping", "loudness", "distortion"),
    _a("Caption Accuracy Agent", Department.GOVERNANCE, Team.QUALITY, "caption accuracy",
       "Verify subtitles match the spoken words, are well-timed and not duplicated.",
       "caption", "subtitle", "accuracy", "timing", "sync"),
    _a("Platform Compliance Agent", Department.GOVERNANCE, Team.QUALITY, "platform compliance",
       "Check each output against the destination platform's policies and specs.",
       "compliance", "policy", "platform", "spec"),
    _a("Human Authenticity Agent", Department.GOVERNANCE, Team.QUALITY, "human authenticity",
       "Ensure the piece reads as genuinely human, not generic AI filler.",
       "authentic", "human", "genuine", "voice"),
    _a("Compliance / Sensitivity Checker", Department.GOVERNANCE, Team.QUALITY, "compliance",
       "Check for ableism, hate, harassment, misinformation and policy risk.",
       "compliance", "sensitivity", "risk", "safety"),
    _a("Quality Control Agent", Department.GOVERNANCE, Team.QUALITY, "quality",
       "Score the 11 quality dimensions and send anything below bar back to improve.",
       "quality", "score", "control"),

    # === PUBLISHING TEAM — approval, scheduling, amplification, recovery =======
    _a("Approval Queue Agent", Department.AUTOMATION, Team.PUBLISHING, "approval queue",
       "Present only clean, high-scoring content to the human approval queue.",
       "approval", "queue", "review", "human"),
    _a("Postiz Scheduler Agent", Department.AUTOMATION, Team.PUBLISHING, "scheduling",
       "Sequence the approved queue across platforms and times via Postiz.",
       "schedule", "queue", "posting", "postiz"),
    _a("Story Amplification Agent", Department.GROWTH, Team.PUBLISHING, "amplification",
       "Amplify approved wins into Stories, reposts and cross-platform pushes.",
       "amplify", "story", "repost", "boost"),
    _a("Content Recovery Agent", Department.AUTOMATION, Team.PUBLISHING, "recovery",
       "Repair near-miss content that failed a gate instead of discarding it.",
       "recovery", "repair", "rescue", "fix"),
    _a("Founder Override Agent", Department.GOVERNANCE, Team.PUBLISHING, "founder override",
       "Give Stephen a final, logged override on any publish decision.",
       "override", "founder", "final", "veto"),
    _a("Campaign Factory Agent", Department.AUTOMATION, Team.PUBLISHING, "campaigns",
       "Expand one topic into a full multi-format campaign with tags and CTAs.",
       "campaign", "factory", "batch"),

    # === LEARNING TEAM — feed results back into INVISABLE_BRAIN ================
    _a("Analytics Agent", Department.ANALYTICS, Team.LEARNING, "analytics",
       "Read performance, find what genuinely resonated, feed learning back.",
       "analytics", "performance", "metrics"),
    _a("Performance Pattern Agent", Department.ANALYTICS, Team.LEARNING, "patterns",
       "Extract repeatable structural patterns from what performed, not one-offs.",
       "pattern", "structure", "repeatable", "performance"),
    _a("Content Graveyard Agent", Department.ANALYTICS, Team.LEARNING, "graveyard",
       "Catalogue what failed and why so the studio never repeats it.",
       "graveyard", "failed", "reject", "lesson"),
    _a("Winning Formula Agent", Department.ANALYTICS, Team.LEARNING, "winning formula",
       "Codify winning formats into reusable, original templates.",
       "winning", "formula", "template", "format"),
    _a("Founder Recognition Agent", Department.ANALYTICS, Team.LEARNING, "founder recognition",
       "Track the Founder Recognition Index and how recognisable Stephen is becoming.",
       "founder", "recognition", "index", "stephen"),
    _a("Repurposing Agent", Department.ANALYTICS, Team.LEARNING, "repurposing",
       "Identify top performers worth repurposing across formats.",
       "repurpose", "recycle"),
    _a("Viral Hook Librarian", Department.GROWTH, Team.LEARNING, "hook library",
       "Save high-performing hooks and remix them into fresh, original openings.",
       "hook", "viral", "library"),
    _a("Comment-to-Content Agent", Department.GROWTH, Team.LEARNING, "comment mining",
       "Turn genuine questions/objections in comments into helpful content.",
       "comment", "faq", "objection", "question"),
    _a("Community Story Agent", Department.GROWTH, Team.LEARNING, "community stories",
       "Categorise consented submitted stories and suggest formats.",
       "story", "community", "submission"),
    _a("Relationship CRM Agent", Department.RELATIONSHIP, Team.LEARNING, "CRM",
       "Maintain ambassador/partner contact history, interests, follow-ups.",
       "crm", "relationship", "ambassador", "follow-up"),
    _a("Partner Growth Agent", Department.RELATIONSHIP, Team.LEARNING, "partner growth",
       "Track partners (CT1, GT Insurance, Bald Builders) and suggest joint campaigns.",
       "partner", "sponsor", "campaign", "ct1"),
    _a("Press/Media Agent", Department.PR, Team.LEARNING, "media",
       "Maintain journalist/podcast databases and suggest which story to pitch.",
       "press", "journalist", "media", "pitch"),
    _a("Press Release Generator", Department.PR, Team.LEARNING, "press releases",
       "Turn campaigns into accurate, media-ready releases.",
       "press release", "announcement"),
    _a("Story Arc Builder", Department.CREATIVE, Team.LEARNING, "repurposing arcs",
       "Turn one idea into a TikTok, Reel, carousel, quote card and founder take.",
       "arc", "repurpose", "flywheel"),

    # === REMIX, PARODY & TREND INTELLIGENCE — a rights-safe remix studio ========
    # Cross-cutting specialists, mapped onto the pipeline teams they serve.
    _a("Trend Scanner Agent", Department.REMIX, Team.RESEARCH, "trend scanning",
       "Scan public sources (trends, construction, tool theft, invisible illness, "
       "autoimmune, pop culture) and abstract them into clean trend signals — never copies.",
       "scan", "trend", "remix", "scanner", "discovery"),
    _a("Pop Culture Curator", Department.REMIX, Team.RESEARCH, "pop culture index",
       "Maintain the film/TV/meme/phrase index with paraphrase-safe versions and "
       "copyright risk; prefer transformation over exact quotes.",
       "pop", "culture", "film", "meme", "quote", "reference"),
    _a("Parody Writer", Department.REMIX, Team.WRITING, "parody",
       "Write original, transformative parody inspired by a trend — British, "
       "self-deprecating, never a copy and never punching down.",
       "parody", "remix", "trend", "skit", "funny"),
    _a("Reaction Script Writer", Department.REMIX, Team.WRITING, "reactions",
       "Write reaction/commentary scripts and duet/stitch ideas where platform rules allow.",
       "reaction", "duet", "stitch", "commentary"),
    _a("Voiceover Remix Agent", Department.REMIX, Team.WRITING, "voiceover remix",
       "Write voiceover scripts to lay over owned/licensed footage; spec the "
       "ElevenLabs + subtitle + FFmpeg job. Never over reference-only material.",
       "voiceover", "remix", "ffmpeg", "subtitle", "elevenlabs"),
    _a("Subtitle & Transcription Agent", Department.REMIX, Team.PRODUCTION, "transcription",
       "Use Whisper/auto-subtitle to transcribe permitted clips, extract hooks, and "
       "generate burned-in captions for vertical video.",
       "whisper", "subtitle", "transcribe", "caption", "hook"),
    _a("Rights & Copyright Officer", Department.REMIX, Team.QUALITY, "rights gating",
       "Classify every media item's rights status and block reuse of anything that "
       "is reference-only or not licensed/owned/CC/public-domain/consented.",
       "rights", "copyright", "licence", "reference", "owned"),
)


def get_agent(name: str) -> Agent | None:
    for a in AGENT_REGISTRY:
        if a.name.lower() == name.lower():
            return a
    return None


def system_prompt_for(name: str) -> str | None:
    agent = get_agent(name)
    return agent.system_prompt() if agent else None


def by_team(team: Team) -> list[Agent]:
    """All agents on a given pipeline team, in registry order."""
    return [a for a in AGENT_REGISTRY if a.team == team]


def pipeline() -> dict[Team, list[Agent]]:
    """The whole studio grouped by team, in pipeline order."""
    return {team: by_team(team) for team in TEAM_ORDER}


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
