"""Remix, Parody & Trend Intelligence Engine.

A large scanner + creative remix brain for INVISABLE®. It scans public
conversation (construction, tool theft, invisible illness, autoimmune updates, pop
culture, TikTok/Instagram trends) and turns what it learns into *original* parody,
reaction, voiceover, meme, and skit content — always on-mission, always British,
never punching down.

It is built around a **rights filter**. The system may analyse, reference, parody,
react to, transform, summarise, and create inspired content; it must never
automatically download and reupload other people's videos as-is. That rule is
enforced by :mod:`invisable_os.guardrails.rights`, which this engine calls before
anything enters production.

Like every engine here it degrades gracefully offline: with no connectors it yields
abstracted baseline trend signals and fully-formed, deterministic creative packs so
the rest of the platform (and the tests) always have something to act on.
"""

from __future__ import annotations

from invisable_os.brain import Memory, get_brain
from invisable_os.engines.connectors import Connector, default_connectors
from invisable_os.guardrails import check, reuse_check
from invisable_os.models.content import Platform
from invisable_os.models.remix import (
    ContentMode,
    CopyrightRisk,
    MemeFormat,
    ParodyScript,
    PermittedAsset,
    PopCultureReference,
    RightsStatus,
    ScannerCategory,
    ScriptVariant,
    TrendItem,
    VideoReference,
    VoiceoverJob,
    is_usable,
)

# --- Which scanner categories each scan button covers ------------------------

SCAN_CATEGORIES: dict[ContentMode, tuple[ScannerCategory, ...]] = {
    ContentMode.SCAN_TRENDS: (
        ScannerCategory.TIKTOK_TRENDS,
        ScannerCategory.INSTAGRAM_TRENDS,
        ScannerCategory.CREATOR_TRENDS,
        ScannerCategory.POPULAR_MEMES,
        ScannerCategory.VIRAL_AUDIO,
    ),
    ContentMode.SCAN_CONSTRUCTION: (
        ScannerCategory.CONSTRUCTION_NEWS,
        ScannerCategory.BUILDERS,
        ScannerCategory.ELECTRICIANS,
        ScannerCategory.PLUMBERS,
        ScannerCategory.ROOFERS,
        ScannerCategory.SITE_SAFETY,
        ScannerCategory.CONSTRUCTION_HUMOUR,
        ScannerCategory.TRADES_MENTAL_HEALTH,
    ),
    ContentMode.SCAN_TOOL_THEFT: (
        ScannerCategory.TOOL_THEFT,
        ScannerCategory.VAN_THEFT,
    ),
    ContentMode.SCAN_INVISIBLE_ILLNESS: (
        ScannerCategory.INVISIBLE_ILLNESS,
        ScannerCategory.CHRONIC_PAIN,
        ScannerCategory.FATIGUE,
        ScannerCategory.DISABILITY_AT_WORK,
    ),
    ContentMode.SCAN_AUTOIMMUNE: (
        ScannerCategory.AUTOIMMUNE,
        ScannerCategory.NHS_UPDATES,
        ScannerCategory.BENEFITS_WORK,
    ),
    ContentMode.SCAN_POP_CULTURE: (
        ScannerCategory.FILM_TV_REFERENCES,
        ScannerCategory.POPULAR_MEMES,
    ),
}

# Default British, on-brand topic seeds per category for the offline baseline.
_CATEGORY_SEEDS: dict[ScannerCategory, str] = {
    ScannerCategory.TIKTOK_TRENDS: "TikTok trends",
    ScannerCategory.INSTAGRAM_TRENDS: "Instagram Reel trends",
    ScannerCategory.CREATOR_TRENDS: "creator trends",
    ScannerCategory.POPULAR_MEMES: "popular memes",
    ScannerCategory.VIRAL_AUDIO: "viral audio formats",
    ScannerCategory.CONSTRUCTION_NEWS: "construction industry news",
    ScannerCategory.BUILDERS: "builders on site",
    ScannerCategory.ELECTRICIANS: "electricians",
    ScannerCategory.PLUMBERS: "plumbers",
    ScannerCategory.ROOFERS: "roofers",
    ScannerCategory.SITE_SAFETY: "site safety",
    ScannerCategory.CONSTRUCTION_HUMOUR: "construction humour",
    ScannerCategory.TRADES_MENTAL_HEALTH: "trades mental health",
    ScannerCategory.TOOL_THEFT: "tool theft",
    ScannerCategory.VAN_THEFT: "van theft",
    ScannerCategory.INVISIBLE_ILLNESS: "invisible illness",
    ScannerCategory.CHRONIC_PAIN: "chronic pain",
    ScannerCategory.FATIGUE: "fatigue",
    ScannerCategory.DISABILITY_AT_WORK: "disability at work",
    ScannerCategory.AUTOIMMUNE: "autoimmune illness",
    ScannerCategory.NHS_UPDATES: "NHS updates",
    ScannerCategory.BENEFITS_WORK: "benefits and work",
    ScannerCategory.FILM_TV_REFERENCES: "film and TV references",
}


# ============================================================================
# Trend Scanner
# ============================================================================


class TrendScanner:
    """Scans public sources and abstracts them into :class:`TrendItem` signals.

    Reuses the same connector contract as the Intelligence Harvester (Feedly,
    Google Trends, Reddit, AnswerThePublic, Perplexity). Offline it yields
    abstracted baseline signals so the remix brain always has direction.
    """

    def __init__(self, connectors: list[Connector] | None = None) -> None:
        self.brain = get_brain()
        self.connectors = connectors if connectors is not None else default_connectors()

    def scan(self, mode: ContentMode) -> list[TrendItem]:
        """Scan for the categories covered by a scan-mode button."""
        categories = SCAN_CATEGORIES.get(mode)
        if not categories:
            raise ValueError(f"{mode} is not a scan mode")
        return self.scan_categories(list(categories))

    def scan_categories(self, categories: list[ScannerCategory]) -> list[TrendItem]:
        topics = [_CATEGORY_SEEDS.get(c, c.value.replace("_", " ")) for c in categories]
        items: list[TrendItem] = []

        # 1. Live connectors — abstracted to our own summaries, never raw copies.
        by_topic = dict(zip(topics, categories, strict=False))
        for connector in self.connectors:
            try:
                for raw in connector.fetch(topics):
                    topic = raw.get("topic", "")
                    category = by_topic.get(topic, categories[0])
                    items.append(
                        TrendItem(
                            title=raw.get("summary", topic)[:120] or topic,
                            category=category,
                            summary=raw.get("summary", ""),
                            why_it_works=raw.get("why", "Resonates with the community."),
                            source_type=raw.get("source_type", connector.name),
                            source_url=raw.get("url", ""),
                            score=float(raw.get("score", 0.5)),
                            invisable_angle=_angle_for(category, topic),
                        )
                    )
            except Exception:  # noqa: BLE001 — a connector must never break a scan
                continue

        # 2. Baseline signals so a scan always returns something actionable.
        covered = {i.category for i in items}
        for category, topic in zip(categories, topics, strict=False):
            if category in covered:
                continue
            items.append(
                TrendItem(
                    title=f"Recurring interest in {topic}",
                    category=category,
                    summary=(
                        f"Steady public interest in '{topic}'. Relatable, honest formats "
                        "with a light British touch tend to land."
                    ),
                    why_it_works="Relatability + honesty beats outrage for this audience.",
                    source_type="aggregate",
                    score=0.7,
                    platforms=["tiktok", "instagram"],
                    invisable_angle=_angle_for(category, topic),
                )
            )

        self._persist(items)
        return items

    def _persist(self, items: list[TrendItem]) -> int:
        for it in items:
            self.brain.remember(
                Memory(
                    text=f"[trend:{it.category}] {it.title}: {it.summary}",
                    kind="trend_signal",
                    metadata={
                        "topic": it.title,
                        "category": it.category.value,
                        "score": it.score,
                        "abstracted": True,
                        "department": "remix",
                    },
                )
            )
        return len(items)


def _angle_for(category: ScannerCategory, topic: str) -> str:
    """A short, on-mission angle for adapting a trend the INVISABLE® way."""
    construction = {
        ScannerCategory.TOOL_THEFT,
        ScannerCategory.VAN_THEFT,
        ScannerCategory.CONSTRUCTION_NEWS,
        ScannerCategory.BUILDERS,
        ScannerCategory.SITE_SAFETY,
        ScannerCategory.CONSTRUCTION_HUMOUR,
        ScannerCategory.TRADES_MENTAL_HEALTH,
    }
    if category in construction:
        return f"Trades-life take on {topic}, tying chaos on site to invisible illness."
    return f"Honest, self-deprecating take on {topic} from someone living with invisible illness."


# ============================================================================
# Rights manager — classification + download gating
# ============================================================================


class RightsManager:
    """Classifies media into a rights status and gates downloads/reuse.

    Classification is conservative by design: unknown third-party video defaults to
    ``reference_only`` with high copyright risk, so nothing is ever reused unless a
    human (or explicit licence evidence) elevates it.
    """

    def classify(
        self,
        url: str,
        *,
        owned: bool = False,
        licensed: bool = False,
        license_note: str = "",
        public_domain: bool = False,
        creative_commons: bool = False,
        user_consent: bool = False,
        duet_stitch_permitted: bool = False,
        blocked: bool = False,
    ) -> VideoReference:
        """Return a :class:`VideoReference` with a conservative rights status."""
        if blocked:
            status, risk = RightsStatus.BLOCKED, CopyrightRisk.HIGH
        elif owned:
            status, risk = RightsStatus.OWNED, CopyrightRisk.NONE
        elif licensed:
            status, risk = RightsStatus.LICENSED, CopyrightRisk.LOW
        elif public_domain:
            status, risk = RightsStatus.PUBLIC_DOMAIN, CopyrightRisk.NONE
        elif creative_commons:
            status, risk = RightsStatus.CREATIVE_COMMONS, CopyrightRisk.LOW
        elif user_consent:
            status, risk = RightsStatus.USER_SUBMITTED_CONSENT, CopyrightRisk.LOW
        elif duet_stitch_permitted:
            status, risk = RightsStatus.PLATFORM_DUET_STITCH, CopyrightRisk.MEDIUM
        else:
            # Default: a link we may learn from but never reupload.
            status, risk = RightsStatus.REFERENCE_ONLY, CopyrightRisk.HIGH

        return VideoReference(
            url=url,
            platform=_platform_from_url(url),
            rights_status=status,
            copyright_risk=risk,
            license_note=license_note,
            transcript_allowed=status != RightsStatus.BLOCKED,
        )

    def plan_download(self, reference: VideoReference) -> dict:
        """Produce a gated yt-dlp plan. Refuses unless the reference is usable."""
        verdict = reuse_check(reference)
        if not verdict.passed:
            return {
                "allowed": False,
                "tool": "yt-dlp",
                "url": reference.url,
                "reason": verdict.violations[0] if verdict.violations else "not usable",
                "rights_status": reference.rights_status.value,
            }
        return {
            "allowed": True,
            "tool": "yt-dlp",
            "url": reference.url,
            "rights_status": reference.rights_status.value,
            "note": "Permitted reuse — licence/ownership on record.",
        }


def _platform_from_url(url: str) -> str:
    u = url.lower()
    for needle, name in (
        ("youtu", "youtube"),
        ("tiktok", "tiktok"),
        ("instagram", "instagram"),
        ("vimeo", "vimeo"),
    ):
        if needle in u:
            return name
    return "site"


# ============================================================================
# Pop-culture & meme index
# ============================================================================

# Seed references — paraphrase-safe and transformative by default. Exact quotes are
# deliberately left empty: the brand prefers original wording over copied lines.
_SEED_POP_CULTURE: tuple[PopCultureReference, ...] = (
    PopCultureReference(
        source_title="Heist-movie tension",
        reference_type="format",
        paraphrase_safe="Treating a stolen drill like the crown jewels.",
        copyright_risk=CopyrightRisk.LOW,
        tone="dry",
        humour_style="trades_banter",
        content_angle="Tool theft as a 'heist', undercut by trades reality.",
        platforms=["tiktok", "instagram"],
        related_topics=["tool_theft", "van_theft"],
    ),
    PopCultureReference(
        source_title="'But you don't look ill' trope",
        reference_type="phrase",
        paraphrase_safe="The look people give when you say you're knackered but 'fine'.",
        copyright_risk=CopyrightRisk.NONE,
        tone="warm",
        humour_style="self_deprecating",
        content_angle="Invisible illness relatability, never bitter.",
        platforms=["tiktok", "instagram"],
        related_topics=["invisible_illness", "fatigue"],
    ),
    PopCultureReference(
        source_title="British sitcom deadpan",
        reference_type="british_comedy",
        paraphrase_safe="Narrating a total disaster in the calmest voice imaginable.",
        copyright_risk=CopyrightRisk.LOW,
        tone="deadpan",
        humour_style="observational",
        content_angle="Van life / site chaos played completely straight.",
        platforms=["tiktok", "instagram", "youtube"],
        related_topics=["construction_humour", "van_theft"],
    ),
)

_SEED_MEME_FORMATS: tuple[MemeFormat, ...] = (
    MemeFormat(
        name="POV format",
        structure="'POV:' + a relatable situation acted out in first person.",
        example_angle="POV: you tell the site you're fine and your body files a complaint.",
        copyright_risk=CopyrightRisk.LOW,
        platforms=["tiktok", "instagram"],
        related_topics=["invisible_illness", "trades_mental_health"],
    ),
    MemeFormat(
        name="Expectation vs reality",
        structure="Two beats: the plan, then the unglamorous reality.",
        example_angle="Expectation: smashing the job. Reality: smashing two paracetamol.",
        copyright_risk=CopyrightRisk.NONE,
        platforms=["tiktok", "instagram"],
        related_topics=["fatigue", "construction_humour"],
    ),
)


class PopCultureIndex:
    """An in-memory, seedable index of pop-culture references and meme formats.

    Persistence lives in the repository; this class is the queryable brain-side
    index used by the parody engine to pick a safe, transformative angle.
    """

    def __init__(
        self,
        references: list[PopCultureReference] | None = None,
        formats: list[MemeFormat] | None = None,
    ) -> None:
        self.references = list(references) if references is not None else list(_SEED_POP_CULTURE)
        self.formats = list(formats) if formats is not None else list(_SEED_MEME_FORMATS)

    def search(self, topic: str, *, limit: int = 5) -> list[PopCultureReference]:
        terms = {t for t in topic.lower().replace("_", " ").split() if len(t) > 2}

        def score(ref: PopCultureReference) -> int:
            hay = " ".join(
                [ref.content_angle, ref.paraphrase_safe, " ".join(ref.related_topics)]
            ).lower()
            return sum(1 for t in terms if t in hay)

        ranked = sorted(self.references, key=score, reverse=True)
        return [r for r in ranked if score(r)][:limit] or self.references[:limit]

    def best_format(self, topic: str) -> MemeFormat | None:
        terms = {t for t in topic.lower().replace("_", " ").split() if len(t) > 2}
        for fmt in self.formats:
            hay = (fmt.example_angle + " " + " ".join(fmt.related_topics)).lower()
            if any(t in hay for t in terms):
                return fmt
        return self.formats[0] if self.formats else None


# ============================================================================
# Parody engine — the creative core
# ============================================================================

_SPONSOR_SAFE_MODES = {ContentMode.CREATE_SPONSOR_SAFE}


class ParodyEngine:
    """Turns a trend/topic into an original, rights-safe, on-brand parody pack."""

    def __init__(self, index: PopCultureIndex | None = None) -> None:
        self.index = index or PopCultureIndex()

    def create(
        self,
        topic: str,
        *,
        mode: ContentMode = ContentMode.CREATE_PARODY,
        source_trend: str = "",
        platforms: list[Platform] | None = None,
        sponsor_safe: bool = False,
    ) -> ParodyScript:
        """Run the parody workflow and return a full, gated pack.

        Steps mirror the directive: analyse the trend, find what makes it land,
        create an *original* INVISABLE® version (never a copy), add British humour
        and the invisible-illness/trades angle, then brand-safety check it.
        """
        topic_clean = topic.strip().rstrip(".") or "life with invisible illness"
        sponsor_safe = sponsor_safe or mode in _SPONSOR_SAFE_MODES
        ref = self.index.search(topic_clean, limit=1)
        ref0 = ref[0] if ref else None
        fmt = self.index.best_format(topic_clean)

        angle = (
            f"{ref0.content_angle} " if ref0 else ""
        ) + f"Original INVISABLE® take on '{topic_clean}': honest, British, self-deprecating."

        variants = self._variants(topic_clean, fmt, sponsor_safe=sponsor_safe)
        caption = self._caption(topic_clean, sponsor_safe=sponsor_safe)
        hashtags = self._hashtags(topic_clean)
        required_visuals = [
            "Owned/licensed B-roll of the situation (site, van, kitchen, sofa)",
            "On-screen captions (Whisper → auto-subtitle, burned in with FFmpeg)",
            "Branded INVISABLE® intro/outro",
        ]
        asset_suggestions = self._asset_suggestions(topic_clean)

        # Brand-safety: run the assembled text through the hard gate.
        full_text = "\n".join(
            [angle, caption, *(v.script for v in variants), *(v.voiceover for v in variants)]
        )
        verdict = check(_as_candidate(full_text))
        risk_flags = list(verdict.risk_flags)
        if ref0 and ref0.exact_quote:
            risk_flags.append("copyright")  # exact quotes raise risk; prefer paraphrase
        risk_score = _risk_score(verdict.passed, risk_flags, sponsor_safe)

        return ParodyScript(
            mode=mode,
            topic=topic_clean,
            source_trend=source_trend,
            angle=angle,
            variants=variants,
            caption=caption,
            hashtags=hashtags,
            tags=[],  # filled from the fixed tag-network at queue time
            required_visuals=required_visuals,
            asset_suggestions=asset_suggestions,
            risk_score=risk_score,
            risk_flags=sorted(set(risk_flags)),
            brand_safe=verdict.passed,
            notes=(
                "Original, transformative content inspired by a trend — not a copy. "
                "Use only rights-safe assets; reference material informs, never reuploaded."
            ),
        )

    # --- variant builders ---------------------------------------------------

    def _variants(
        self, topic: str, fmt: MemeFormat | None, *, sponsor_safe: bool
    ) -> list[ScriptVariant]:
        pov = (fmt.example_angle if fmt else f"POV: {topic} wins again, and so do I — eventually.")
        hook = f"POV: {topic} vs me, and somehow I'm still standing."
        beat = "" if sponsor_safe else " (yes, I checked the van twice)"
        body = (
            f"So {topic} happened again today{beat}. My body had already clocked off, "
            "my to-do list hadn't. Honestly? You just laugh, or you'd cry."
        )
        cta = "Tag someone who gets it. We see you. — INVISABLE®"
        return [
            ScriptVariant(
                label="tiktok_15s",
                platform=Platform.TIKTOK,
                duration_seconds=15,
                script=f"{hook}\n{pov}\n{cta}",
                voiceover=f"{hook} {pov}",
            ),
            ScriptVariant(
                label="reel_30s",
                platform=Platform.INSTAGRAM,
                duration_seconds=30,
                script=f"{hook}\n{body}\n{cta}",
                voiceover=f"{hook} {body}",
            ),
            ScriptVariant(
                label="voiceover",
                platform=Platform.TIKTOK,
                duration_seconds=20,
                script=body,
                voiceover=body,
            ),
            ScriptVariant(
                label="skit",
                platform=Platform.INSTAGRAM,
                duration_seconds=25,
                script=(
                    f"SCENE — me, deadpan to camera: '{hook}'\n"
                    f"CUT — the chaos of {topic}.\n"
                    f"BACK to me, calm as anything: '{body}'\n"
                    f"CARD: {cta}"
                ),
                voiceover=f"{hook} {body}",
            ),
        ]

    def _caption(self, topic: str, *, sponsor_safe: bool) -> str:
        if sponsor_safe:
            return (
                f"Some days {topic} tests you. We keep showing up anyway. "
                "Proud to do this work with people who get it. #InvisibleIllness"
            )
        return (
            f"{topic.capitalize()} again, is it? My immune system and I had words. "
            "If you know, you know. You're not alone in this."
        )

    def _hashtags(self, topic: str) -> list[str]:
        base = ["#INVISABLE", "#InvisibleIllness", "#YouDontLookSick"]
        t = topic.lower()
        if any(k in t for k in ("tool", "van", "site", "trade", "build")):
            base += ["#Trades", "#ToolTheft", "#ConstructionUK"]
        if any(k in t for k in ("autoimmune", "fatigue", "pain", "chronic", "illness")):
            base += ["#ChronicIllness", "#Autoimmune", "#Spoonie"]
        return base[:8]

    def _asset_suggestions(self, topic: str) -> list[str]:
        return [
            "Owned founder-filmed B-roll (status: owned)",
            "Licensed music bed from the approved library (status: licensed)",
            "Public-domain / Creative Commons cutaways with attribution (status: cc)",
            "Platform-native duet/stitch ONLY where the creator permits it",
            "NEVER: downloading and reuploading someone else's clip (reference_only)",
        ]


def _risk_score(passed: bool, risk_flags: list[str], sponsor_safe: bool) -> float:
    if not passed:
        return 1.0
    score = min(0.2 * len(risk_flags), 0.8)
    if sponsor_safe:
        score = min(score + 0.1, 1.0)  # sponsor work warrants extra scrutiny
    return round(score, 3)


def _as_candidate(text: str):
    from invisable_os.models.content import ContentCandidate, ContentFormat

    return ContentCandidate(
        brief="remix parody check",
        platform=Platform.TIKTOK,
        content_format=ContentFormat.SHORT_VIDEO,
        body=text,
    )


# ============================================================================
# Voiceover engine — script over APPROVED footage only
# ============================================================================


class VoiceoverEngine:
    """Builds a voiceover job that overlays a script onto *usable* footage only."""

    def build(
        self,
        asset: PermittedAsset,
        script: str,
        *,
        voice_style: str = "founder",
        platform: Platform = Platform.TIKTOK,
        caption_style: str = "bold_centered",
    ) -> VoiceoverJob:
        """Assemble the ElevenLabs + subtitle + FFmpeg job, gated on rights."""
        verdict = reuse_check(asset)
        if not verdict.passed:
            return VoiceoverJob(
                clip_asset_id=asset.id,
                clip_rights_status=asset.rights_status,
                script=script,
                voice_style=voice_style,
                platform=platform,
                caption_style=caption_style,
                approved=False,
                blocked_reason=verdict.violations[0] if verdict.violations else "unusable rights",
            )

        export = "tiktok_9x16" if platform == Platform.TIKTOK else "reel_9x16"
        return VoiceoverJob(
            clip_asset_id=asset.id,
            clip_rights_status=asset.rights_status,
            script=script,
            voice_style=voice_style,
            platform=platform,
            caption_style=caption_style,
            elevenlabs_request={
                "voice": voice_style,
                "text": script,
                "model": "eleven_multilingual_v2",
            },
            subtitle_format="srt",
            ffmpeg_job={
                "input": asset.uri or f"asset://{asset.id}",
                "steps": [
                    "trim", "resize_9x16", "overlay_voiceover",
                    "burn_subtitles", "add_branded_intro_outro",
                ],
                "export": export,
            },
            export_format=export,
            approved=False,  # still routes through the human approval queue
        )


# ============================================================================
# Department facade — dispatches the 15 PWA modes
# ============================================================================


class RemixTrendEngine:
    """The Remix, Parody & Trend Intelligence department, wired as one engine.

    ``run(mode, ...)`` dispatches the 15 PWA buttons: the six SCAN_* modes return
    trend items; the nine CREATE_* modes return creative packs. Everything passes
    through the rights filter and the brand-safety gate before it is returned.
    """

    SCAN_MODES = frozenset(SCAN_CATEGORIES)
    CREATE_MODES = frozenset(set(ContentMode) - set(SCAN_CATEGORIES))

    def __init__(
        self,
        scanner: TrendScanner | None = None,
        parody: ParodyEngine | None = None,
        voiceover: VoiceoverEngine | None = None,
        rights: RightsManager | None = None,
        index: PopCultureIndex | None = None,
    ) -> None:
        self.index = index or PopCultureIndex()
        self.scanner = scanner or TrendScanner()
        self.parody = parody or ParodyEngine(self.index)
        self.voiceover = voiceover or VoiceoverEngine()
        self.rights = rights or RightsManager()

    def run(self, mode: ContentMode, *, topic: str = "", source_trend: str = "") -> dict:
        """Dispatch a PWA mode. Returns a JSON-serialisable result dict."""
        mode = ContentMode(mode)
        if mode in self.SCAN_MODES:
            items = self.scanner.scan(mode)
            return {
                "mode": mode.value,
                "kind": "scan",
                "count": len(items),
                "items": [i.model_dump() for i in items],
            }

        # Creative modes. A few set their own defaults.
        topic = topic.strip()
        sponsor_safe = mode == ContentMode.CREATE_SPONSOR_SAFE
        if not topic:
            topic = _DEFAULT_TOPIC.get(mode, "life with invisible illness")

        if mode == ContentMode.CREATE_MEME_BATCH:
            return {
                "mode": mode.value,
                "kind": "meme_batch",
                "topic": topic,
                "memes": [m.model_dump() for m in self.create_meme_batch(topic)],
            }

        pack = self.parody.create(
            topic, mode=mode, source_trend=source_trend, sponsor_safe=sponsor_safe
        )
        return {"mode": mode.value, "kind": "creative", "pack": pack.model_dump()}

    def create_meme_batch(self, topic: str, *, count: int = 3) -> list[ParodyScript]:
        """A small batch of meme-format packs around a topic."""
        formats = self.index.formats[:count] or [None]
        out: list[ParodyScript] = []
        for fmt in formats:
            label = fmt.name if fmt else "meme"
            out.append(
                self.parody.create(
                    f"{topic} ({label})", mode=ContentMode.CREATE_MEME_BATCH
                )
            )
        return out

    def usable_assets(self, assets: list[PermittedAsset]) -> list[PermittedAsset]:
        """Filter to assets whose rights permit reuse (helper for the studio)."""
        return [a for a in assets if is_usable(a.rights_status)]

    # --- High-level workflows (the PWA "commands") -------------------------

    def suggest_angles(self, topic: str, *, n: int = 5) -> list[str]:
        """Workflow 1, step 7: suggest N on-mission INVISABLE® angles for a topic."""
        topic = (topic.strip().rstrip(".") or "life with invisible illness")
        refs = self.index.search(topic, limit=2)
        ref_angle = refs[0].content_angle if refs else ""
        templates = [
            f"Honest, self-deprecating take on {topic} from someone with invisible illness.",
            f"Trades-banter version of {topic}, played completely deadpan.",
            f"'POV' skit: {topic} vs a body that's already clocked off.",
            f"Educational explainer: what {topic} really feels like, no clinical jargon.",
            f"Sponsor-safe awareness angle on {topic} — supportive, no false claims.",
            f"Community 'you're not alone' reframe of {topic}.",
            (
                f"{ref_angle}" if ref_angle
                else f"Myth-buster: the thing people get wrong about {topic}."
            ),
        ]
        # De-dupe while preserving order.
        seen, out = set(), []
        for t in templates:
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out[:n]

    def scan_to_ideas(self, mode_or_topic: ContentMode | str) -> dict:
        """The "Scan tool theft today" command: topics + idea bundles + tags.

        Accepts a scan ``ContentMode`` (uses its categories) or a free-text topic.
        """
        if isinstance(mode_or_topic, ContentMode) or mode_or_topic in set(ContentMode):
            mode = ContentMode(mode_or_topic)
            items = self.scanner.scan(mode)
            topic = items[0].title if items else mode.value.replace("scan_", "").replace("_", " ")
        else:
            topic = str(mode_or_topic)
            items = self.scanner.scan_categories([ScannerCategory.CREATOR_TRENDS])

        topics = [{"title": i.title, "summary": i.summary, "score": i.score} for i in items]
        return {
            "topic": topic,
            "topics": topics,
            "tiktok_ideas": self.suggest_angles(topic, n=5),
            "reels_ideas": [f"Reel: {a}" for a in self.suggest_angles(topic, n=5)],
            "humour_angles": [
                f"Deadpan trades-banter on {topic}.",
                f"Self-deprecating 'my body vs {topic}' bit.",
                f"Expectation vs reality around {topic}.",
            ],
            "serious_angles": [
                f"Awareness explainer on {topic}.",
                f"'You're not alone' community message about {topic}.",
                f"Honest founder reflection on {topic}.",
            ],
            "sponsor_safe_angles": [
                f"Supportive, claim-free partner tie-in on {topic}.",
                f"Educational sponsor segment about {topic}.",
            ],
            "suggested_tags": [],  # filled from the fixed tag-network at queue time
            "suggested_hashtags": self.parody._hashtags(topic),
        }

    def reference_to_parody(self, url: str, *, topic: str = "") -> dict:
        """Workflow 2: a reference link → rights warning + summary + original parody.

        The reference is marked ``reference_only`` by default and is NEVER treated as
        reusable footage — it only inspires an original script.
        """
        reference = self.rights.classify(url)  # defaults to reference_only
        download = self.rights.plan_download(reference)
        topic = topic or "this trend"
        pack = self.parody.create(topic, mode=ContentMode.CREATE_PARODY, source_trend=url)
        return {
            "rights_warning": (
                "Reference only — analysed for inspiration. This clip will NOT be "
                "downloaded or reuploaded; the output below is original INVISABLE® content."
            ),
            "reference": reference.model_dump(),
            "download_plan": download,
            "trend_summary": f"Why it works: relatable, punchy framing of {topic}.",
            "pack": pack.model_dump(),
        }

    def construction_news_to_content(self, topic: str) -> dict:
        """Workflow 5: one construction/tool-theft story → a family of angles."""
        topic = topic.strip().rstrip(".") or "tool theft"
        serious = self.parody.create(topic, mode=ContentMode.CREATE_PARODY)
        humour = self.parody.create(topic, mode=ContentMode.CREATE_TRADES_HUMOUR)
        sponsor = self.parody.create(topic, mode=ContentMode.CREATE_SPONSOR_SAFE, sponsor_safe=True)
        return {
            "topic": topic,
            "summary": f"Abstracted summary of current activity around {topic}.",
            "serious_awareness": serious.model_dump(),
            "humour": humour.model_dump(),
            "trades_banter": self.parody.create(
                f"{topic} on a Monday", mode=ContentMode.CREATE_TRADES_HUMOUR
            ).model_dump(),
            "invisable_tie_in": (
                f"Tie {topic} back to invisible illness: the stress you can't see is real too."
            ),
            "sponsor_safe": sponsor.model_dump(),
        }

    def pop_culture_to_version(self, reference_id_or_topic: str) -> dict:
        """Workflow 4: a pop-culture reference → paraphrase-safe INVISABLE® versions."""
        matches = [r for r in self.index.references if r.id == reference_id_or_topic]
        if matches:
            ref = matches[0]
        else:
            found = self.index.search(reference_id_or_topic, limit=1)
            ref = found[0] if found else None
        topic = (ref.content_angle if ref else reference_id_or_topic) or "invisible illness"
        risk = ref.copyright_risk.value if ref else CopyrightRisk.MEDIUM.value
        pack = self.parody.create(topic, mode=ContentMode.CREATE_PARODY)
        return {
            "reference": ref.model_dump() if ref else None,
            "copyright_risk": risk,
            "paraphrase_safe": ref.paraphrase_safe if ref else "",
            "guidance": "Prefer the paraphrase-safe version; do not overuse exact quotes.",
            "pack": pack.model_dump(),
        }

    def video_plan(self, pack: ParodyScript) -> dict:
        """Workflow 3 / export: a rights-safe FFmpeg shot/assembly plan for a pack."""
        return {
            "topic": pack.topic,
            "rights_note": (
                "Assemble from rights-safe assets only "
                "(owned/licensed/public_domain/creative_commons/consented/duet-stitch)."
            ),
            "required_visuals": pack.required_visuals,
            "asset_suggestions": pack.asset_suggestions,
            "ffmpeg_steps": [
                "ingest_rights_safe_clips",
                "trim_to_beats",
                "resize_9x16",
                "overlay_voiceover (ElevenLabs)",
                "burn_subtitles (Whisper → auto-subtitle)",
                "add_branded_intro_outro",
                "export_tiktok_reels",
            ],
            "variants": [v.model_dump() for v in pack.variants],
        }


_DEFAULT_TOPIC: dict[ContentMode, str] = {
    ContentMode.CREATE_TRADES_HUMOUR: "a chaotic day on site",
    ContentMode.CREATE_FOUNDER_SKIT: "running a movement on no spoons",
    ContentMode.CREATE_TIKTOK_TREND: "the current TikTok trend",
    ContentMode.CREATE_INSTAGRAM_REEL: "the current Reel trend",
    ContentMode.CREATE_REACTION: "a trending clip worth reacting to",
    ContentMode.CREATE_VOICEOVER_REMIX: "a relatable situation",
}


__all__ = [
    "SCAN_CATEGORIES",
    "TrendScanner",
    "RightsManager",
    "PopCultureIndex",
    "ParodyEngine",
    "VoiceoverEngine",
    "RemixTrendEngine",
]
