"""Remix, Parody & Trend Intelligence department.

The single most important behaviour under test is the rights filter: the system
may analyse/parody/transform, but must never download-and-reupload reference-only
or blocked material. Everything else (scanner, pop-culture index, parody/voiceover
generation, persistence) is exercised offline and deterministically.
"""

from invisable_os.agents import AGENT_REGISTRY, get_agent
from invisable_os.agents.registry import Department
from invisable_os.engines.remix import (
    ParodyEngine,
    PopCultureIndex,
    RemixTrendEngine,
    RightsManager,
    TrendScanner,
    VoiceoverEngine,
)
from invisable_os.guardrails import can_download, filter_usable, reuse_check
from invisable_os.models.remix import (
    USABLE_RIGHTS,
    ContentMode,
    CopyrightRisk,
    PermittedAsset,
    PopCultureReference,
    RightsStatus,
    is_usable,
)
from invisable_os.store import get_repository

# --- Rights model -----------------------------------------------------------


def test_usable_rights_set_is_exactly_the_six_permitted():
    assert USABLE_RIGHTS == {
        RightsStatus.OWNED,
        RightsStatus.LICENSED,
        RightsStatus.PUBLIC_DOMAIN,
        RightsStatus.CREATIVE_COMMONS,
        RightsStatus.USER_SUBMITTED_CONSENT,
        RightsStatus.PLATFORM_DUET_STITCH,
    }
    assert not is_usable(RightsStatus.REFERENCE_ONLY)
    assert not is_usable(RightsStatus.BLOCKED)
    assert all(is_usable(s) for s in USABLE_RIGHTS)


def test_is_usable_handles_unknown_strings():
    assert is_usable("owned") is True
    assert is_usable("nonsense") is False


# --- Rights guardrail (the hard gate) ---------------------------------------


def test_reuse_check_blocks_reference_only_and_blocked():
    ok = PermittedAsset(title="van clip", rights_status=RightsStatus.OWNED)
    ref = PermittedAsset(title="ripped clip", rights_status=RightsStatus.REFERENCE_ONLY)
    blocked = PermittedAsset(title="nope", rights_status=RightsStatus.BLOCKED)

    assert reuse_check(ok).passed is True
    assert reuse_check(ref).passed is False
    assert "reference_only" in reuse_check(ref).violations[0]
    assert reuse_check(blocked).passed is False
    # A mixed list fails as a whole if any item is unusable.
    assert reuse_check([ok, ref]).passed is False


def test_can_download_only_for_usable_references():
    rights = RightsManager()
    ref_only = rights.classify("https://youtube.com/watch?v=abc")  # default reference_only
    owned = rights.classify("https://my.site/clip.mp4", owned=True)
    assert can_download(ref_only) is False
    assert can_download(owned) is True


def test_filter_usable_drops_unusable_assets():
    assets = [
        PermittedAsset(title="a", rights_status=RightsStatus.OWNED),
        PermittedAsset(title="b", rights_status=RightsStatus.REFERENCE_ONLY),
        PermittedAsset(title="c", rights_status=RightsStatus.CREATIVE_COMMONS),
    ]
    kept = filter_usable(assets)
    assert {a.title for a in kept} == {"a", "c"}


# --- Rights manager ---------------------------------------------------------


def test_classify_defaults_to_reference_only_high_risk():
    ref = RightsManager().classify("https://tiktok.com/@x/video/1")
    assert ref.rights_status == RightsStatus.REFERENCE_ONLY
    assert ref.copyright_risk == CopyrightRisk.HIGH
    assert ref.downloadable is False
    assert ref.platform == "tiktok"


def test_classify_owned_and_licensed_are_usable():
    rights = RightsManager()
    assert rights.classify("u", owned=True).rights_status == RightsStatus.OWNED
    assert rights.classify("u", licensed=True).rights_status == RightsStatus.LICENSED
    assert rights.classify("u", creative_commons=True).downloadable is True


def test_plan_download_refuses_reference_only():
    rights = RightsManager()
    plan = rights.plan_download(rights.classify("https://youtu.be/x"))
    assert plan["allowed"] is False
    assert plan["tool"] == "yt-dlp"


# --- Trend scanner ----------------------------------------------------------


def test_scanner_returns_items_for_every_scan_mode():
    scanner = TrendScanner()
    for mode in RemixTrendEngine.SCAN_MODES:
        items = scanner.scan(mode)
        assert items, f"{mode} returned no items"
        assert all(i.summary for i in items)


def test_scanner_rejects_a_create_mode():
    import pytest

    with pytest.raises(ValueError):
        TrendScanner().scan(ContentMode.CREATE_PARODY)


# --- Pop-culture index ------------------------------------------------------


def test_pop_culture_index_seeded_and_searchable():
    index = PopCultureIndex()
    assert index.references and index.formats
    hits = index.search("tool theft")
    assert hits
    # Seeds prefer transformative paraphrase over exact quotes.
    assert all(not r.exact_quote for r in index.references)
    assert index.best_format("invisible illness") is not None


# --- Parody engine ----------------------------------------------------------


def test_parody_pack_has_all_required_variants_and_is_brand_safe():
    pack = ParodyEngine().create("tool theft and invisible illness")
    labels = {v.label for v in pack.variants}
    assert {"tiktok_15s", "reel_30s", "voiceover", "skit"} <= labels
    assert pack.caption and pack.hashtags
    assert pack.required_visuals and pack.asset_suggestions
    assert pack.brand_safe is True
    assert 0.0 <= pack.risk_score <= 1.0
    # Self-deprecating, first-person humour passes the punch-down gate.
    assert pack.risk_score == 0.0


def test_parody_asset_suggestions_never_endorse_reupload():
    pack = ParodyEngine().create("van theft")
    joined = " ".join(pack.asset_suggestions).lower()
    assert "never" in joined  # explicitly warns against reuploading others' clips
    assert any("owned" in s.lower() or "licensed" in s.lower() for s in pack.asset_suggestions)


def test_exact_quote_reference_raises_copyright_risk():
    risky = PopCultureReference(
        source_title="A film",
        exact_quote="A copyrighted line said verbatim",
        paraphrase_safe="",
        related_topics=["tool_theft"],
    )
    index = PopCultureIndex(references=[risky])
    pack = ParodyEngine(index).create("tool_theft")
    assert "copyright" in pack.risk_flags
    assert pack.risk_score > 0.0


# --- Voiceover engine -------------------------------------------------------


def test_voiceover_builds_over_owned_footage():
    asset = PermittedAsset(title="van", rights_status=RightsStatus.OWNED, uri="asset://van")
    job = VoiceoverEngine().build(asset, "A funny line about trades and fatigue.")
    assert job.blocked_reason == ""
    assert job.elevenlabs_request["text"]
    assert "burn_subtitles" in job.ffmpeg_job["steps"]


def test_voiceover_blocked_over_reference_only_footage():
    asset = PermittedAsset(title="ripped", rights_status=RightsStatus.REFERENCE_ONLY)
    job = VoiceoverEngine().build(asset, "x")
    assert job.approved is False
    assert job.blocked_reason
    assert job.elevenlabs_request == {}


# --- Department facade -------------------------------------------------------


def test_engine_dispatches_scan_modes():
    out = RemixTrendEngine().run(ContentMode.SCAN_TOOL_THEFT)
    assert out["kind"] == "scan"
    assert out["count"] >= 1


def test_engine_dispatches_create_modes():
    out = RemixTrendEngine().run(ContentMode.CREATE_TRADES_HUMOUR)
    assert out["kind"] == "creative"
    assert out["pack"]["variants"]


def test_engine_meme_batch():
    out = RemixTrendEngine().run(ContentMode.CREATE_MEME_BATCH, topic="fatigue")
    assert out["kind"] == "meme_batch"
    assert len(out["memes"]) >= 1


def test_scan_to_ideas_bundle_shape():
    out = RemixTrendEngine().scan_to_ideas(ContentMode.SCAN_TOOL_THEFT)
    for key in ("tiktok_ideas", "reels_ideas", "humour_angles",
                "serious_angles", "sponsor_safe_angles", "suggested_hashtags"):
        assert out[key], f"missing {key}"
    assert len(out["tiktok_ideas"]) == 5


def test_reference_to_parody_warns_and_stays_reference_only():
    out = RemixTrendEngine().reference_to_parody(
        "https://www.tiktok.com/@x/video/1", topic="a trend"
    )
    assert "reference" in out["rights_warning"].lower()
    assert out["reference"]["rights_status"] == "reference_only"
    assert out["download_plan"]["allowed"] is False
    assert out["pack"]["variants"]


def test_construction_news_to_content_returns_all_angles():
    out = RemixTrendEngine().construction_news_to_content("tool theft")
    for key in ("serious_awareness", "humour", "trades_banter",
                "invisable_tie_in", "sponsor_safe"):
        assert out[key]


def test_pop_culture_to_version_prefers_paraphrase():
    out = RemixTrendEngine().pop_culture_to_version("tool theft")
    assert "paraphrase" in out["guidance"].lower()
    assert out["pack"]["brand_safe"] is True


def test_video_plan_is_rights_safe():
    pack = ParodyEngine().create("van theft")
    plan = RemixTrendEngine().video_plan(pack)
    assert "rights-safe" in plan["rights_note"].lower()
    assert "burn_subtitles (Whisper → auto-subtitle)" in plan["ffmpeg_steps"]


# --- Persistence ------------------------------------------------------------


def test_repository_round_trips_remix_tables():
    repo = get_repository()
    sid = repo.add_scanner_source({"name": "Feedly trades", "type": "rss",
                                   "topic_area": "tool_theft"})
    assert sid
    assert repo.list_scanner_sources()

    repo.add_scanned_item({"title": "Tool theft up again", "rights_status": "reference_only"})
    items = repo.list_scanned_items()
    assert items and items[0]["rights_status"] == "reference_only"

    aid = repo.add_media_asset({"title": "van clip", "rights_status": "owned"})
    assert repo.get_media_asset(aid)["rights_status"] == "owned"
    updated = repo.set_asset_rights(aid, "licensed", licence_notes="MSA #12")
    assert updated["rights_status"] == "licensed"
    assert repo.list_media_assets(rights_status="licensed")

    repo.add_pop_culture({"title": "Heist tension", "paraphrase_safe": "guarding a drill"})
    repo.add_meme_format({"format_name": "POV", "structure": "POV: ..."})
    assert repo.list_pop_culture() and repo.list_meme_formats()


def test_repository_remix_job_lifecycle():
    repo = get_repository()
    jid = repo.add_remix_job({"input_topic": "tool theft", "mode": "create_parody",
                              "approval_status": "pending_review"})
    assert repo.list_remix_jobs(approval_status="pending_review")
    approved = repo.set_remix_job_status(jid, "approved")
    assert approved["approval_status"] == "approved"


# --- Agents -----------------------------------------------------------------


def test_remix_agents_registered_with_guardrails():
    remix_agents = [a for a in AGENT_REGISTRY if a.department == Department.REMIX]
    assert len(remix_agents) >= 6
    officer = get_agent("Rights & Copyright Officer")
    assert officer is not None
    assert "PRIME DIRECTIVE" in officer.system_prompt()
