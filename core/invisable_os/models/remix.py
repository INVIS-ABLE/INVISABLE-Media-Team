"""Remix, Parody & Trend Intelligence domain models.

These models back the Remix department: the scanner (sources + trend items), the
rights database (every media item carries a :class:`RightsStatus`), the pop-culture
index, and the creative jobs (parody packs, voiceover jobs, meme batches).

The single most important rule in this department lives here as data, not prose:
**only assets whose rights status is in :data:`USABLE_RIGHTS` may be used in
generated media.** Everything else — most importantly ``reference_only`` — can
*inspire* original content but can never be reuploaded as-is. The guardrail in
:mod:`invisable_os.guardrails.rights` enforces this; these models make it explicit.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field

from invisable_os.models.content import Platform

# ============================================================================
# Rights & copyright — the heart of the department
# ============================================================================


class RightsStatus(StrEnum):
    """The rights status every media item must carry before it can be touched."""

    OWNED = "owned"
    LICENSED = "licensed"
    PUBLIC_DOMAIN = "public_domain"
    CREATIVE_COMMONS = "creative_commons"
    USER_SUBMITTED_CONSENT = "user_submitted_consent"
    PLATFORM_DUET_STITCH = "platform_duet_stitch"
    REFERENCE_ONLY = "reference_only"
    BLOCKED = "blocked"


# The ONLY statuses that may appear in generated/published media. Everything else
# (reference_only, blocked) can inspire ideas but must never be reuploaded as-is.
USABLE_RIGHTS: frozenset[RightsStatus] = frozenset(
    {
        RightsStatus.OWNED,
        RightsStatus.LICENSED,
        RightsStatus.PUBLIC_DOMAIN,
        RightsStatus.CREATIVE_COMMONS,
        RightsStatus.USER_SUBMITTED_CONSENT,
        RightsStatus.PLATFORM_DUET_STITCH,
    }
)


def is_usable(status: RightsStatus | str) -> bool:
    """True only for rights statuses that may be used in generated media."""
    try:
        return RightsStatus(status) in USABLE_RIGHTS
    except ValueError:
        return False


class CopyrightRisk(StrEnum):
    """How risky reusing a reference would be — advisory, set by classification."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# Scanner — sources and abstracted trend items
# ============================================================================


class ScannerCategory(StrEnum):
    """What the scanner monitors. Drives both discovery and tagging of trends."""

    # Construction / trades
    CONSTRUCTION_NEWS = "construction_news"
    TOOL_THEFT = "tool_theft"
    VAN_THEFT = "van_theft"
    TRADES_JOBS = "trades_jobs"
    SELF_EMPLOYED_TRADES = "self_employed_trades"
    BUILDERS = "builders"
    ELECTRICIANS = "electricians"
    PLUMBERS = "plumbers"
    ROOFERS = "roofers"
    HGV = "hgv"
    SITE_SAFETY = "site_safety"
    CONSTRUCTION_HUMOUR = "construction_humour"
    TRADES_MENTAL_HEALTH = "trades_mental_health"
    # Invisible / chronic illness
    INVISIBLE_ILLNESS = "invisible_illness"
    AUTOIMMUNE = "autoimmune"
    CHRONIC_PAIN = "chronic_pain"
    FATIGUE = "fatigue"
    DISABILITY_AT_WORK = "disability_at_work"
    BENEFITS_WORK = "benefits_work"
    NHS_UPDATES = "nhs_updates"
    CHARITY_SECTOR = "charity_sector"
    # Culture / platform trends
    TIKTOK_TRENDS = "tiktok_trends"
    INSTAGRAM_TRENDS = "instagram_trends"
    CREATOR_TRENDS = "creator_trends"
    POPULAR_MEMES = "popular_memes"
    FILM_TV_REFERENCES = "film_tv_references"
    VIRAL_AUDIO = "viral_audio"


class ScannedSource(BaseModel):
    """A feed/source the scanner monitors (Feedly, Reddit, Google Trends, …)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    url: str = ""
    kind: str = "rss"  # rss | trends | forum | search | questions | research
    category: ScannerCategory = ScannerCategory.INVISIBLE_ILLNESS
    enabled: bool = True
    notes: str = ""


class TrendItem(BaseModel):
    """An abstracted trend signal — our own summary, never copied raw content."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str
    category: ScannerCategory = ScannerCategory.TIKTOK_TRENDS
    summary: str = ""  # our abstraction of what is happening / why it resonates
    why_it_works: str = ""  # what makes it funny / viral / shareable
    source_type: str = "aggregate"
    source_url: str = ""  # stored as a *reference link*, never as content to reupload
    score: float = 0.5
    platforms: list[str] = Field(default_factory=list)
    invisable_angle: str = ""  # how INVISABLE® could adapt it on-mission


class ReferenceLink(BaseModel):
    """A saved link kept purely as a reference. Never a download-and-reupload."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    url: str
    title: str = ""
    note: str = ""
    rights_status: RightsStatus = RightsStatus.REFERENCE_ONLY
    category: ScannerCategory = ScannerCategory.CREATOR_TRENDS


# ============================================================================
# Video / reference handling (yt-dlp · FFmpeg · Whisper)
# ============================================================================


class VideoReference(BaseModel):
    """A video the system is aware of, with an explicit rights status.

    A reference is *not* permission to download. Only references whose
    ``rights_status`` is usable may ever be fetched (and only for permitted reuse);
    ``reference_only`` material can inform a script but must never be reuploaded.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    url: str
    title: str = ""
    platform: str = ""  # youtube | tiktok | instagram | vimeo | site
    rights_status: RightsStatus = RightsStatus.REFERENCE_ONLY
    copyright_risk: CopyrightRisk = CopyrightRisk.HIGH
    license_note: str = ""  # licence/permission evidence when usable
    transcript_allowed: bool = True  # transcription for *analysis* is permitted
    notes: str = ""

    @property
    def downloadable(self) -> bool:
        """yt-dlp may only fetch usable, non-blocked references."""
        return is_usable(self.rights_status)


class PermittedAsset(BaseModel):
    """An asset cleared for use in generated media (owned/licensed/CC/etc.)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str
    asset_type: str = "video"  # video | audio | image | voice | broll | music
    uri: str = ""  # path / DAM reference (AtroDAM, ResourceSpace)
    rights_status: RightsStatus = RightsStatus.OWNED
    license_note: str = ""
    attribution: str = ""  # required for some Creative Commons licences
    tags: list[str] = Field(default_factory=list)

    @property
    def usable(self) -> bool:
        return is_usable(self.rights_status)


class SubtitleCue(BaseModel):
    """One subtitle cue (Whisper → SRT/ASS via auto-subtitle/FFmpeg)."""

    start: float = 0.0  # seconds
    end: float = 0.0
    text: str = ""


class Subtitle(BaseModel):
    """A generated subtitle track for an asset."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    asset_id: str = ""
    language: str = "en"
    format: str = "srt"  # srt | ass | vtt
    cues: list[SubtitleCue] = Field(default_factory=list)


class ExtractedHook(BaseModel):
    """A strong line / moment surfaced from a transcript for reuse as a hook."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source_ref: str = ""  # video_reference id or transcript id
    text: str = ""
    timestamp: float = 0.0
    strength: float = 0.5


# ============================================================================
# Pop-culture & meme index
# ============================================================================


class PopCultureReference(BaseModel):
    """A film/TV/meme/phrase reference, with copyright risk and a safe paraphrase.

    Prefer ``paraphrase_safe`` (transformative, original wording) over ``exact_quote``.
    Exact quotes carry copyright risk and must not be overused.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source_title: str
    reference_type: str = "film"  # film | tv | british_comedy | meme | phrase | format
    exact_quote: str = ""  # only stored where permitted; do not overuse
    paraphrase_safe: str = ""  # original, transformative wording — preferred
    copyright_risk: CopyrightRisk = CopyrightRisk.MEDIUM
    tone: str = ""  # dry | warm | absurd | deadpan | wholesome
    humour_style: str = ""  # self_deprecating | observational | trades_banter
    content_angle: str = ""  # how to use it for INVISABLE®
    platforms: list[str] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)


class MemeFormat(BaseModel):
    """A reusable meme/format template (structure learned, not content copied)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    structure: str = ""  # our own description of the format's mechanics
    example_angle: str = ""  # an on-brand INVISABLE® use of it
    copyright_risk: CopyrightRisk = CopyrightRisk.LOW
    platforms: list[str] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)


# ============================================================================
# Creative jobs — parody, voiceover, remix
# ============================================================================


class ContentMode(StrEnum):
    """The PWA buttons — what the operator can ask the department to do."""

    SCAN_TRENDS = "scan_trends"
    SCAN_CONSTRUCTION = "scan_construction"
    SCAN_TOOL_THEFT = "scan_tool_theft"
    SCAN_INVISIBLE_ILLNESS = "scan_invisible_illness"
    SCAN_AUTOIMMUNE = "scan_autoimmune"
    SCAN_POP_CULTURE = "scan_pop_culture"
    CREATE_PARODY = "create_parody"
    CREATE_REACTION = "create_reaction"
    CREATE_VOICEOVER_REMIX = "create_voiceover_remix"
    CREATE_MEME_BATCH = "create_meme_batch"
    CREATE_TRADES_HUMOUR = "create_trades_humour"
    CREATE_FOUNDER_SKIT = "create_founder_skit"
    CREATE_SPONSOR_SAFE = "create_sponsor_safe"
    CREATE_TIKTOK_TREND = "create_tiktok_trend"
    CREATE_INSTAGRAM_REEL = "create_instagram_reel"


class ScriptVariant(BaseModel):
    """One scripted variant of a parody/remix (e.g. a 15s TikTok cut)."""

    label: str  # e.g. "tiktok_15s" | "reel_30s" | "voiceover" | "skit"
    platform: Platform = Platform.TIKTOK
    duration_seconds: int = 15
    script: str = ""
    voiceover: str = ""


class ParodyScript(BaseModel):
    """A full parody/remix pack ready for the approval queue.

    Mirrors the directive's example output: TikTok + Reel + voiceover + skit
    scripts, caption, hashtags, tags, required visuals, rights-safe asset
    suggestions, and a risk score.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    mode: ContentMode = ContentMode.CREATE_PARODY
    topic: str = ""
    source_trend: str = ""  # the trend/reference/link that inspired it
    angle: str = ""  # what makes it land + the INVISABLE® twist
    variants: list[ScriptVariant] = Field(default_factory=list)
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    required_visuals: list[str] = Field(default_factory=list)
    asset_suggestions: list[str] = Field(default_factory=list)  # rights-safe only
    risk_score: float = 0.0  # 0 (safe) – 1 (needs careful review)
    risk_flags: list[str] = Field(default_factory=list)
    brand_safe: bool = True
    notes: str = ""


class VoiceoverJob(BaseModel):
    """A voiceover-over-approved-footage job: script → ElevenLabs → subtitles → FFmpeg."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    clip_asset_id: str = ""  # MUST reference a usable PermittedAsset
    clip_rights_status: RightsStatus = RightsStatus.OWNED
    script: str = ""
    voice_style: str = "founder"
    platform: Platform = Platform.TIKTOK
    caption_style: str = "bold_centered"
    elevenlabs_request: dict = Field(default_factory=dict)
    subtitle_format: str = "srt"
    ffmpeg_job: dict = Field(default_factory=dict)
    export_format: str = "tiktok_9x16"
    approved: bool = False
    blocked_reason: str = ""


class RemixJob(BaseModel):
    """A higher-level remix request joining a trend/reference to an output mode."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    mode: ContentMode = ContentMode.CREATE_PARODY
    topic: str = ""
    reference_url: str = ""
    rights_status: RightsStatus = RightsStatus.REFERENCE_ONLY
    status: str = "queued"  # queued | generated | needs_review | blocked
    parody_script_id: str = ""
    notes: str = ""


class PlatformRule(BaseModel):
    """A platform's rule the department must respect (duet/stitch/reuse policy)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    platform: str = "tiktok"
    rule: str = ""  # e.g. "duet allowed when creator enables it"
    allows_duet: bool = False
    allows_stitch: bool = False
    allows_reupload: bool = False
    notes: str = ""
