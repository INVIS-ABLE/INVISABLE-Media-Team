"""Remix, Parody & Trend Intelligence API.

The HTTP surface for the Remix department: the scanner, the rights manager, the
remix studio, the pop-culture index, and the voiceover queue. Thin wiring — all the
logic (and the rights filter) lives in the engine and the guardrails.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from invisable_os.engines.remix import PopCultureIndex, RemixTrendEngine
from invisable_os.guardrails import RIGHTS_RULE, reuse_check
from invisable_os.guardrails.rights import RightsVerdict
from invisable_os.models.content import Platform
from invisable_os.models.remix import (
    USABLE_RIGHTS,
    ContentMode,
    MemeFormat,
    ParodyScript,
    PermittedAsset,
    PopCultureReference,
    RightsStatus,
    ScannedSource,
    VideoReference,
)
from invisable_os.store import get_repository

remix_router = APIRouter(prefix="/v1", tags=["remix"])


def _engine() -> RemixTrendEngine:
    return RemixTrendEngine()


# --- requests ---------------------------------------------------------------


class ScanRequest(BaseModel):
    mode: ContentMode = ContentMode.SCAN_TRENDS
    persist: bool = True


class ManualLinkRequest(BaseModel):
    url: str = ""
    topic: str = ""
    title: str = ""
    owned: bool = False
    licensed: bool = False
    public_domain: bool = False
    creative_commons: bool = False
    user_consent: bool = False
    duet_stitch_permitted: bool = False
    blocked: bool = False


class RemixCreateRequest(BaseModel):
    mode: ContentMode = ContentMode.CREATE_PARODY
    topic: str = ""
    source_trend: str = ""
    reference_url: str = ""
    sponsor_safe: bool = False
    persist: bool = True


class IdeasRequest(BaseModel):
    topic: str = ""
    mode: ContentMode | None = None


class MediaUploadRequest(BaseModel):
    title: str = ""
    file_path: str = ""
    source_url: str = ""
    asset_type: str = "video"
    owner: str = ""
    rights_status: RightsStatus = RightsStatus.OWNED
    licence_notes: str = ""
    consent_id: str = ""
    allowed_platforms: list[str] = Field(default_factory=list)
    allowed_uses: list[str] = Field(default_factory=list)
    blocked_uses: list[str] = Field(default_factory=list)


class RightsPatchRequest(BaseModel):
    rights_status: RightsStatus
    licence_notes: str | None = None


class VoiceoverCreateRequest(BaseModel):
    asset_id: str
    script: str
    voice_style: str = "founder"
    platform: Platform = Platform.TIKTOK
    caption_style: str = "bold_centered"


class VideoPlanRequest(BaseModel):
    pack: ParodyScript


# --- rights -----------------------------------------------------------------


@remix_router.get("/rights")
def rights_statuses() -> dict:
    """The rights status system and the copyright rule, from the source of truth."""
    return {
        "rule": RIGHTS_RULE,
        "all_statuses": [s.value for s in RightsStatus],
        "usable_in_media": sorted(s.value for s in USABLE_RIGHTS),
        "inspiration_only": ["reference_only"],
        "never_use": ["reference_only", "blocked"],
    }


class RightsCheckRequest(BaseModel):
    assets: list[PermittedAsset] = Field(default_factory=list)
    references: list[VideoReference] = Field(default_factory=list)


@remix_router.post("/rights/check")
def rights_check(req: RightsCheckRequest) -> RightsVerdict:
    """Gate a set of assets/references before they enter production."""
    return reuse_check([*req.assets, *req.references])


# --- scanner ----------------------------------------------------------------


@remix_router.post("/scanner/source")
def add_scanner_source(source: ScannedSource) -> dict:
    """Register a scanner source (Feedly/Reddit/Google Trends/…)."""
    payload = source.model_dump()
    payload["topic_area"] = source.category.value
    payload["type"] = source.kind
    return {"id": get_repository().add_scanner_source(payload)}


@remix_router.get("/scanner/sources")
def list_scanner_sources() -> dict:
    return {"sources": get_repository().list_scanner_sources()}


@remix_router.post("/scanner/scan")
def run_scan(req: ScanRequest) -> dict:
    """Run a scan-mode button. Persists abstracted items to the reference inbox."""
    result = _engine().run(req.mode)
    if req.persist and result.get("kind") == "scan":
        repo = get_repository()
        for item in result["items"]:
            repo.add_scanned_item(
                {
                    "title": item["title"],
                    "url": item.get("source_url", ""),
                    "platform": ",".join(item.get("platforms", [])),
                    "summary": item.get("summary", ""),
                    "topic_tags": [item.get("category", "")],
                    "trend_score": item.get("score", 0.0),
                    "rights_status": "reference_only",
                }
            )
    return result


@remix_router.get("/scanner/items")
def list_scanned_items(status: str | None = None) -> dict:
    return {"items": get_repository().list_scanned_items(status=status)}


@remix_router.post("/scanner/manual-link")
def manual_link(req: ManualLinkRequest) -> dict:
    """Workflow 1/2 entry: add a manual link/topic, classify rights, suggest angles.

    A bare link defaults to ``reference_only`` — it can inspire ideas but is never
    treated as reusable footage.
    """
    engine = _engine()
    reference = engine.rights.classify(
        req.url or req.topic,
        owned=req.owned,
        licensed=req.licensed,
        public_domain=req.public_domain,
        creative_commons=req.creative_commons,
        user_consent=req.user_consent,
        duet_stitch_permitted=req.duet_stitch_permitted,
        blocked=req.blocked,
    )
    topic = req.topic or req.title or "this reference"
    item_id = get_repository().add_scanned_item(
        {
            "url": req.url,
            "title": req.title or topic,
            "platform": reference.platform,
            "summary": f"Manually added reference for '{topic}'.",
            "rights_status": reference.rights_status.value,
            "risk_score": {"none": 0.0, "low": 0.2, "medium": 0.5, "high": 0.8}[
                reference.copyright_risk.value
            ],
        }
    )
    return {
        "id": item_id,
        "reference": reference.model_dump(),
        "download_plan": engine.rights.plan_download(reference),
        "suggested_angles": engine.suggest_angles(topic),
    }


# --- remix studio -----------------------------------------------------------


@remix_router.get("/remix/modes")
def remix_modes() -> dict:
    """The 15 PWA buttons, grouped into scan and create modes."""
    return {
        "scan_modes": sorted(m.value for m in RemixTrendEngine.SCAN_MODES),
        "create_modes": sorted(m.value for m in RemixTrendEngine.CREATE_MODES),
    }


def _persist_job(result: dict, *, topic: str, reference_url: str = "") -> str | None:
    """Persist a creative result as a remix job; returns the job id (or None)."""
    pack = result.get("pack") or (result.get("memes") or [{}])[0]
    if not pack:
        return None
    variant = (pack.get("variants") or [{}])[0]
    return get_repository().add_remix_job(
        {
            "input_topic": topic,
            "reference_item_id": reference_url,
            "output_type": result.get("mode", "parody"),
            "mode": result.get("mode", "create_parody"),
            "script": variant.get("script", ""),
            "voiceover_script": variant.get("voiceover", ""),
            "caption": pack.get("caption", ""),
            "hashtags": pack.get("hashtags", []),
            "tags": pack.get("tags", []),
            "platform": variant.get("platform", ""),
            "rights_check_status": "passed",
            "brand_check_status": "passed" if pack.get("brand_safe", True) else "needs_review",
            "approval_status": "pending_review",
            "risk_score": pack.get("risk_score", 0.0),
            "pack": pack,
        }
    )


@remix_router.post("/remix/create")
def remix_create(req: RemixCreateRequest) -> dict:
    """Run any of the 9 create-modes (or a scan-mode) and optionally queue it."""
    engine = _engine()
    if req.reference_url:
        result = engine.reference_to_parody(req.reference_url, topic=req.topic)
        result["mode"] = ContentMode.CREATE_PARODY.value
    else:
        result = engine.run(req.mode, topic=req.topic, source_trend=req.source_trend)
    job_id = None
    if req.persist and result.get("kind") in {"creative", "meme_batch"} or "pack" in result:
        job_id = _persist_job(result, topic=req.topic, reference_url=req.reference_url)
    return {**result, "job_id": job_id}


@remix_router.post("/remix/scan-to-ideas")
def scan_to_ideas(req: IdeasRequest) -> dict:
    """The "Scan tool theft today" command — topics + idea bundles + hashtags."""
    engine = _engine()
    return engine.scan_to_ideas(req.mode or req.topic)


@remix_router.post("/remix/reference-to-parody")
def reference_to_parody(req: RemixCreateRequest) -> dict:
    """Workflow 2: a reference link → rights warning + original parody."""
    return _engine().reference_to_parody(req.reference_url, topic=req.topic)


@remix_router.post("/remix/construction-news")
def construction_news(req: IdeasRequest) -> dict:
    """Workflow 5: a construction/tool-theft story → a family of angles."""
    return _engine().construction_news_to_content(req.topic)


@remix_router.post("/remix/pop-culture")
def pop_culture_version(req: IdeasRequest) -> dict:
    """Workflow 4: a pop-culture reference → paraphrase-safe INVISABLE® versions."""
    return _engine().pop_culture_to_version(req.topic)


@remix_router.get("/remix/jobs")
def list_remix_jobs(status: str | None = None) -> dict:
    return {"jobs": get_repository().list_remix_jobs(approval_status=status)}


@remix_router.post("/remix/jobs/{job_id}/{action}")
def remix_job_action(job_id: str, action: str) -> dict:
    mapping = {
        "approve": "approved",
        "reject": "rejected",
        "queue": "pending_review",
    }
    status = mapping.get(action)
    if status is None:
        return {"error": f"unknown action '{action}'", "allowed": list(mapping)}
    job = get_repository().set_remix_job_status(job_id, status)
    return job or {"error": "not found", "id": job_id}


# --- media / rights manager -------------------------------------------------


@remix_router.post("/media/upload")
def media_upload(req: MediaUploadRequest) -> dict:
    """Register a media asset with its rights metadata (no binary upload here)."""
    return {"id": get_repository().add_media_asset(req.model_dump())}


@remix_router.get("/media")
def list_media(rights_status: str | None = None) -> dict:
    return {"assets": get_repository().list_media_assets(rights_status=rights_status)}


@remix_router.patch("/media/{asset_id}/rights")
def patch_media_rights(asset_id: str, req: RightsPatchRequest) -> dict:
    updated = get_repository().set_asset_rights(
        asset_id, req.rights_status.value, licence_notes=req.licence_notes
    )
    return updated or {"error": "not found", "id": asset_id}


# --- voiceover queue --------------------------------------------------------


@remix_router.post("/voiceover/create")
def voiceover_create(req: VoiceoverCreateRequest) -> dict:
    """Build a voiceover job over an APPROVED asset. Gated on rights."""
    repo = get_repository()
    asset_row = repo.get_media_asset(req.asset_id)
    if asset_row is None:
        return {"error": "asset not found", "id": req.asset_id}
    asset = PermittedAsset(
        id=asset_row["id"],
        title=asset_row.get("title", ""),
        asset_type=asset_row.get("asset_type", "video"),
        uri=asset_row.get("file_path") or asset_row.get("source_url", ""),
        rights_status=RightsStatus(asset_row.get("rights_status", "owned")),
        license_note=asset_row.get("licence_notes", ""),
    )
    job = _engine().voiceover.build(
        asset,
        req.script,
        voice_style=req.voice_style,
        platform=req.platform,
        caption_style=req.caption_style,
    )
    return job.model_dump()


# --- export -----------------------------------------------------------------


@remix_router.post("/export/video-plan")
def export_video_plan(req: VideoPlanRequest) -> dict:
    """A rights-safe FFmpeg shot/assembly plan for a parody pack."""
    return _engine().video_plan(req.pack)


# --- pop-culture index ------------------------------------------------------


@remix_router.get("/popculture")
def list_pop_culture() -> dict:
    stored = get_repository().list_pop_culture()
    if stored:
        return {"references": stored, "source": "store"}
    # Fall back to the seeded in-memory index so the screen is never empty.
    return {
        "references": [r.model_dump() for r in PopCultureIndex().references],
        "source": "seed",
    }


@remix_router.post("/popculture")
def add_pop_culture(ref: PopCultureReference) -> dict:
    return {"id": get_repository().add_pop_culture(ref.model_dump())}


@remix_router.get("/meme-formats")
def list_meme_formats() -> dict:
    stored = get_repository().list_meme_formats()
    if stored:
        return {"formats": stored, "source": "store"}
    return {"formats": [m.model_dump() for m in PopCultureIndex().formats], "source": "seed"}


@remix_router.post("/meme-formats")
def add_meme_format(fmt: MemeFormat) -> dict:
    return {"id": get_repository().add_meme_format(fmt.model_dump())}
