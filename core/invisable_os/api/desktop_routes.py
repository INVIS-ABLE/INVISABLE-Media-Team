"""Desktop API surface — the routes the INVISABLE® Media desktop apps talk to.

These ``/api/*`` endpoints are the *contract* between the server (source of truth)
and the two desktop apps:

* **Command Centre** (server/admin) — reads every queue, the warchest, account
  status, and the render-job board; drives manual overrides (approve/reject/
  schedule/post-now, pause/resume automation, create content requests).
* **Studio Worker** (5090) — polls for render jobs, claims them, reports progress,
  uploads finished assets, and marks jobs complete/failed.

They are deliberately thin: HTTP → existing engines/services/repository. The richer
internal ``/v1/*`` surface stays as-is; this module adds the stable, desktop-shaped
names the apps depend on, and the worker/job + automation-pause machinery they need.

Auth: when ``INVISABLE_DESKTOP_TOKEN`` (or ``INVISABLE_API_TOKEN``) is set, every
``/api/*`` request must present it as ``Authorization: Bearer <token>``. With no
token configured (local/LAN dev) the surface is open — exactly the posture the
server takes behind Cloudflare Access / on the trusted home LAN.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from invisable_os import __version__
from invisable_os.config import get_settings
from invisable_os.models.content import QueueStatus
from invisable_os.services import publish_due, reserve_health, schedule_next
from invisable_os.store import get_repository

api_router = APIRouter(prefix="/api", tags=["desktop"])


# --- Auth -------------------------------------------------------------------

# Worker kinds the 5090 Studio app can run (mirrors the desktop worker manifest).
WORKER_JOB_KINDS = [
    "ffmpeg_render",
    "whisper_caption",
    "comfyui_image",
    "comfyui_video",
    "audio_cleanup",
    "caption_render",
    "format_convert",
    "upload",
]


def _expected_token() -> str | None:
    return os.getenv("INVISABLE_DESKTOP_TOKEN") or os.getenv("INVISABLE_API_TOKEN")


def require_token(authorization: str | None = Header(default=None)) -> None:
    """Gate ``/api/*`` on a server-issued bearer token when one is configured.

    Credentials never live in the desktop frontend — the app stores this token in
    OS-safe storage and sends it here. With no token set the surface stays open for
    localhost/LAN use behind Cloudflare Access.
    """
    expected = _expected_token()
    if not expected:
        return
    presented = ""
    if authorization and authorization.lower().startswith("bearer "):
        presented = authorization[7:].strip()
    if presented != expected:
        raise HTTPException(status_code=401, detail="invalid or missing API token")


# --- Health & system status -------------------------------------------------


@api_router.get("/health")
def api_health() -> dict:
    """Unauthenticated liveness probe — used by the desktop URL-priority resolver."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "invisable-media",
        "version": __version__,
        "brand": settings.brand_name,
        "auth_required": _expected_token() is not None,
    }


def _automation_state(repo) -> dict:
    automation = repo.get_flag("automation", {"paused": False, "reason": ""})
    posting = repo.get_flag("posting", {"paused": False, "reason": ""})
    accounts = repo.get_flag("account_pause", {})
    return {
        "automation_paused": bool(automation.get("paused")),
        "automation_reason": automation.get("reason", ""),
        "posting_paused": bool(posting.get("paused")),
        "paused_accounts": [k for k, v in accounts.items() if v],
        "emergency_pause": bool(automation.get("paused")),
    }


@api_router.get("/system/status", dependencies=[Depends(require_token)])
def api_system_status() -> dict:
    """The single snapshot the desktop top bar renders every few seconds."""
    repo = get_repository()
    counts = repo.counts_by_status()
    jobs = repo.render_job_counts()
    automation = _automation_state(repo)

    scheduled = counts.get(QueueStatus.SCHEDULED.value, 0)
    return {
        "ok": True,
        "version": __version__,
        "queue_counts": counts,
        "pending_jobs": jobs.get("queued", 0) + jobs.get("claimed", 0),
        "processing_jobs": jobs.get("processing", 0),
        "failed_jobs": jobs.get("failed", 0),
        "completed_jobs": jobs.get("completed", 0),
        "job_counts": jobs,
        "posts_scheduled_today": scheduled,
        "pending_review": counts.get(QueueStatus.PENDING_REVIEW.value, 0),
        **automation,
        "integrations": _integration_flags(),
    }


def _integration_flags() -> dict:
    import shutil

    return {
        "postiz": bool(os.getenv("POSTIZ_API_URL") and os.getenv("POSTIZ_API_KEY")),
        "comfyui": bool(os.getenv("COMFYUI_BASE_URL")),
        "whisper": shutil.which("whisper") is not None
        or bool(os.getenv("WHISPER_MODEL")),
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
        "claude": bool(os.getenv("ANTHROPIC_API_KEY")),
    }


# --- Accounts ---------------------------------------------------------------


@api_router.get("/accounts", dependencies=[Depends(require_token)])
def api_accounts() -> dict:
    """Connected social accounts, derived from channels + integration config.

    Real connection/OAuth is handled server-side by Postiz/n8n; the desktop app only
    reads status and triggers server routes — credentials never reach the frontend.
    """
    repo = get_repository()
    channels = repo.list_channels()
    postiz_ready = bool(os.getenv("POSTIZ_API_URL") and os.getenv("POSTIZ_API_KEY"))
    paused = repo.get_flag("account_pause", {})
    accounts = []
    for ch in channels:
        handle = ch.get("handle") or ch.get("name") or ch.get("id")
        accounts.append(
            {
                "id": ch.get("id"),
                "platform": ch.get("platform", ""),
                "handle": handle,
                "connected": postiz_ready,
                "paused": bool(paused.get(ch.get("id")) or paused.get(handle)),
                "status": "connected" if postiz_ready else "needs-connection",
            }
        )
    return {"accounts": accounts, "postiz_configured": postiz_ready}


class AccountConnectRequest(BaseModel):
    platform: str
    handle: str = ""


@api_router.post("/accounts/connect", dependencies=[Depends(require_token)])
def api_account_connect(req: AccountConnectRequest) -> dict:
    """Trigger a server-side account connection flow (Postiz/n8n owns the OAuth).

    Returns where the operator should complete the connection; we never accept or
    store platform credentials through the desktop app.
    """
    postiz_url = os.getenv("POSTIZ_API_URL", "")
    return {
        "ok": True,
        "platform": req.platform,
        "handled_by": "postiz",
        "next": "complete-oauth-in-postiz",
        "postiz_url": postiz_url,
        "note": "Account connections are completed server-side in Postiz; the desktop "
        "app only triggers this route. No credentials pass through the client.",
    }


# --- Queue / warchest -------------------------------------------------------


@api_router.get("/queue", dependencies=[Depends(require_token)])
def api_queue(status: str | None = None) -> dict:
    repo = get_repository()
    return {"counts": repo.counts_by_status(), "items": repo.list_queue(status=status)}


@api_router.get("/calendar", dependencies=[Depends(require_token)])
def api_calendar() -> dict:
    """Scheduled posts grouped by ISO date, for the Scheduled Posts calendar view."""
    from invisable_os.services import calendar

    return {"calendar": calendar()}


@api_router.get("/warchest", dependencies=[Depends(require_token)])
def api_warchest(category: str | None = None, reserve_status: str | None = "ready") -> dict:
    repo = get_repository()
    return {
        "health": reserve_health(),
        "items": repo.list_war_chest(category=category, reserve_status=reserve_status),
    }


# --- Jobs (the 5090 Studio worker board) ------------------------------------


class JobCreateRequest(BaseModel):
    kind: str = Field(default="ffmpeg_render")
    title: str = ""
    queue_item_id: str = ""
    priority: int = Field(default=5, ge=1, le=10)
    params: dict = Field(default_factory=dict)


class JobClaimRequest(BaseModel):
    worker_id: str = "studio-5090"


class JobCompleteRequest(BaseModel):
    result: dict = Field(default_factory=dict)
    error: str = ""


class JobProgressRequest(BaseModel):
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str | None = None
    log: str | None = None


@api_router.get("/jobs", dependencies=[Depends(require_token)])
def api_jobs(status: str | None = None, kind: str | None = None) -> dict:
    repo = get_repository()
    return {
        "counts": repo.render_job_counts(),
        "jobs": repo.list_render_jobs(status=status, kind=kind),
    }


@api_router.get("/jobs/render", dependencies=[Depends(require_token)])
def api_render_jobs() -> dict:
    """Jobs the 5090 worker can run — the render board."""
    repo = get_repository()
    jobs = [
        j
        for j in repo.list_render_jobs()
        if j["status"] in ("queued", "claimed", "processing")
    ]
    return {"jobs": jobs, "kinds": WORKER_JOB_KINDS}


@api_router.post("/jobs/create", dependencies=[Depends(require_token)])
def api_job_create(req: JobCreateRequest) -> dict:
    if req.kind not in WORKER_JOB_KINDS:
        raise HTTPException(status_code=422, detail=f"unknown job kind '{req.kind}'")
    repo = get_repository()
    job = repo.create_render_job(
        req.kind,
        title=req.title,
        queue_item_id=req.queue_item_id,
        priority=req.priority,
        params=req.params,
    )
    return {"ok": True, "job": job}


@api_router.post("/jobs/next/claim", dependencies=[Depends(require_token)])
def api_job_claim_next(req: JobClaimRequest, kinds: str | None = None) -> dict:
    """Worker convenience: atomically claim the next runnable job for this worker."""
    repo = get_repository()
    wanted = [k for k in (kinds or "").split(",") if k] or None
    job = repo.claim_next_render_job(req.worker_id, kinds=wanted)
    return {"ok": job is not None, "job": job}


@api_router.post("/jobs/{job_id}/claim", dependencies=[Depends(require_token)])
def api_job_claim(job_id: str, req: JobClaimRequest) -> dict:
    job = get_repository().claim_render_job(job_id, req.worker_id)
    if job is None:
        raise HTTPException(status_code=409, detail="job not claimable")
    return {"ok": True, "job": job}


@api_router.post("/jobs/{job_id}/progress", dependencies=[Depends(require_token)])
def api_job_progress(job_id: str, req: JobProgressRequest) -> dict:
    fields: dict = {"progress": req.progress}
    if req.status:
        fields["status"] = req.status
    if req.log:
        fields["log"] = req.log
    job = get_repository().update_render_job(job_id, **fields)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True, "job": job}


@api_router.post("/jobs/{job_id}/complete", dependencies=[Depends(require_token)])
def api_job_complete(job_id: str, req: JobCompleteRequest) -> dict:
    job = get_repository().complete_render_job(job_id, result=req.result, error=req.error)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True, "job": job}


@api_router.post("/jobs/{job_id}/cancel", dependencies=[Depends(require_token)])
def api_job_cancel(job_id: str) -> dict:
    job = get_repository().cancel_render_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"ok": True, "job": job}


# --- Assets: upload finished media from the 5090 ----------------------------


def _upload_dir() -> Path:
    """Where the server keeps assets uploaded by the worker (env-overridable)."""
    base = os.getenv("INVISABLE_UPLOAD_DIR", "./data/uploads")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


@api_router.post("/assets/upload", dependencies=[Depends(require_token)])
async def api_asset_upload(
    file: UploadFile,
    job_id: str = "",
    queue_item_id: str = "",
    kind: str = "render",
) -> dict:
    """Receive a finished asset from the Studio worker and register it server-side."""
    dest_dir = _upload_dir()
    safe_name = os.path.basename(file.filename or "asset.bin")
    dest = dest_dir / (f"{job_id}_{safe_name}" if job_id else safe_name)
    size = 0
    with dest.open("wb") as fh:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            fh.write(chunk)

    repo = get_repository()
    asset_path = str(dest)
    if queue_item_id:
        try:
            repo.add_media_asset(
                queue_item_id,
                kind=kind,
                spec="uploaded",
                path=asset_path,
                backend="studio-upload",
            )
        except Exception:  # noqa: BLE001 — registration is best-effort
            pass
    if job_id:
        job = repo.get_render_job(job_id)
        if job is not None:
            result = dict(job.get("result") or {})
            result.setdefault("assets", []).append(asset_path)
            repo.update_render_job(job_id, result=result, log=f"uploaded {safe_name}")
    return {"ok": True, "path": asset_path, "bytes": size, "filename": safe_name}


# --- Posts: detail + manual content edits -----------------------------------


@api_router.get("/posts/{post_id}", dependencies=[Depends(require_token)])
def api_post_get(post_id: str) -> dict:
    """Full post detail — candidate text + its media — for the editor view."""
    repo = get_repository()
    item = repo.get_queue_item(post_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"post '{post_id}' not found")
    return {"post": item, "media": repo.list_media(post_id)}


class PostEditRequest(BaseModel):
    """Manual edits to a post's content (any field omitted is left untouched)."""

    caption: str | None = None  # -> candidate.body (the main caption/script)
    hook: str | None = None
    call_to_action: str | None = None
    hashtags: list[str] | None = None


@api_router.post("/posts/{post_id}/edit", dependencies=[Depends(require_token)])
def api_post_edit(post_id: str, req: PostEditRequest) -> dict:
    """Edit Caption / Edit Hashtags (and hook/CTA) — Stephen's manual override."""
    patch: dict = {}
    if req.caption is not None:
        patch["body"] = req.caption
    if req.hook is not None:
        patch["hook"] = req.hook
    if req.call_to_action is not None:
        patch["call_to_action"] = req.call_to_action
    if req.hashtags is not None:
        patch["hashtags"] = req.hashtags
    if not patch:
        raise HTTPException(status_code=422, detail="no editable fields provided")
    item = get_repository().update_queue_candidate(post_id, candidate_patch=patch)
    if item is None:
        raise HTTPException(status_code=404, detail=f"post '{post_id}' not found")
    return {"ok": True, "post": item}


class ReplaceMediaRequest(BaseModel):
    media_path: str
    kind: str = "primary"


@api_router.post("/posts/{post_id}/replace-media", dependencies=[Depends(require_token)])
def api_post_replace_media(post_id: str, req: ReplaceMediaRequest) -> dict:
    """Replace Media — point a post at a different (already-uploaded) asset path."""
    repo = get_repository()
    item = repo.get_queue_item(post_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"post '{post_id}' not found")
    repo.add_media_asset(
        post_id,
        kind=req.kind,
        spec="replacement",
        path=req.media_path,
        backend="manual",
    )
    updated = repo.update_queue_candidate(
        post_id, candidate_patch={"primary_media": req.media_path}
    )
    return {"ok": True, "post": updated, "media": repo.list_media(post_id)}


# --- Posts: manual overrides ------------------------------------------------


def _transition_or_404(item_id: str, status: QueueStatus) -> dict:
    item = get_repository().transition(item_id, status)
    if item is None:
        raise HTTPException(status_code=404, detail=f"post '{item_id}' not found")
    return item


@api_router.post("/posts/{post_id}/approve", dependencies=[Depends(require_token)])
def api_post_approve(post_id: str) -> dict:
    return {"ok": True, "post": _transition_or_404(post_id, QueueStatus.APPROVED)}


class RejectRequest(BaseModel):
    reason: str = ""


@api_router.post("/posts/{post_id}/reject", dependencies=[Depends(require_token)])
def api_post_reject(post_id: str, req: RejectRequest | None = None) -> dict:
    return {"ok": True, "post": _transition_or_404(post_id, QueueStatus.REJECTED)}


@api_router.post("/posts/{post_id}/schedule", dependencies=[Depends(require_token)])
def api_post_schedule(post_id: str) -> dict:
    """Assign the next open posting slot for the item's channel."""
    result = schedule_next(post_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, **result}


@api_router.post("/posts/{post_id}/post-now", dependencies=[Depends(require_token)])
def api_post_now(post_id: str) -> dict:
    """Publish immediately: approve-if-needed, then run the publisher."""
    repo = get_repository()
    item = repo.get_queue_item(post_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"post '{post_id}' not found")
    if item.get("status") not in (QueueStatus.APPROVED.value, QueueStatus.SCHEDULED.value):
        repo.transition(post_id, QueueStatus.APPROVED)
    published = repo.transition(post_id, QueueStatus.PUBLISHED)
    result = publish_due()
    return {"ok": True, "post": published, "publish": result}


@api_router.post("/posts/{post_id}/push-to-story", dependencies=[Depends(require_token)])
def api_post_push_to_story(post_id: str) -> dict:
    repo = get_repository()
    item = repo.get_queue_item(post_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"post '{post_id}' not found")
    job = repo.create_render_job(
        "format_convert",
        title=f"Story cut · {item.get('slot_label', post_id)}",
        queue_item_id=post_id,
        priority=3,
        params={"target": "story", "ratio": "9:16"},
    )
    return {"ok": True, "story_job": job}


@api_router.post("/posts/{post_id}/recycle", dependencies=[Depends(require_token)])
def api_post_recycle(post_id: str) -> dict:
    """Send a published post back to the warchest for reuse."""
    repo = get_repository()
    item = repo.get_queue_item(post_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"post '{post_id}' not found")
    recycled = repo.transition(post_id, QueueStatus.APPROVED)
    return {"ok": True, "post": recycled}


# --- Automation: pause / resume (emergency override) ------------------------


class PauseRequest(BaseModel):
    scope: str = Field(default="all")  # all | posting | account
    account: str = ""
    reason: str = ""


@api_router.post("/automation/pause", dependencies=[Depends(require_token)])
def api_automation_pause(req: PauseRequest) -> dict:
    repo = get_repository()
    if req.scope == "posting":
        repo.set_flag("posting", {"paused": True, "reason": req.reason})
    elif req.scope == "account" and req.account:
        flags = repo.get_flag("account_pause", {})
        flags[req.account] = True
        repo.set_flag("account_pause", flags)
    else:  # all
        repo.set_flag("automation", {"paused": True, "reason": req.reason or "manual"})
    return {"ok": True, "state": _automation_state(repo)}


@api_router.post("/automation/resume", dependencies=[Depends(require_token)])
def api_automation_resume(req: PauseRequest) -> dict:
    repo = get_repository()
    if req.scope == "posting":
        repo.set_flag("posting", {"paused": False, "reason": ""})
    elif req.scope == "account" and req.account:
        flags = repo.get_flag("account_pause", {})
        flags[req.account] = False
        repo.set_flag("account_pause", flags)
    else:  # all
        repo.set_flag("automation", {"paused": False, "reason": ""})
    return {"ok": True, "state": _automation_state(repo)}


# --- Content: ask the factory for something specific ------------------------


class ContentRequest(BaseModel):
    brief: str
    platform: str = "instagram"
    content_format: str = "short_video"
    count: int = Field(default=1, ge=1, le=50)
    campaign: bool = False
    create_render_job: bool = True


@api_router.post("/content/request", dependencies=[Depends(require_token)])
def api_content_request(req: ContentRequest) -> dict:
    """Stephen asks for specific content; run the tournament and queue the winners.

    Optionally also spawns a render job so the 5090 can produce the assets. This is
    the manual 'Generate New Post / Generate Campaign / Create Specific Content
    Request' button wired straight to the Content Tournament Engine.
    """
    from invisable_os.engines.tournament import ContentTournamentEngine
    from invisable_os.models.content import ContentFormat, Platform

    try:
        platform = Platform(req.platform)
    except ValueError:
        platform = Platform.INSTAGRAM
    try:
        content_format = ContentFormat(req.content_format)
    except ValueError:
        content_format = ContentFormat.SHORT_VIDEO

    select = max(1, req.count)
    engine = ContentTournamentEngine()
    result = engine.run(
        req.brief,
        platform,
        count=max(24, select * 8),
        select=select,
        content_format=content_format,
    )

    repo = get_repository()
    job = None
    if req.create_render_job:
        job = repo.create_render_job(
            "ffmpeg_render",
            title=f"Requested: {req.brief[:60]}",
            priority=2 if req.campaign else 4,
            params={"brief": req.brief, "platform": req.platform, "campaign": req.campaign},
        )
    return {"ok": True, "tournament": result.summary(), "render_job": job}
