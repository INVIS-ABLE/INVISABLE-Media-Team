"""End-to-end contract tests for the desktop apps.

These drive the *exact* call sequences the Rust desktop clients use, against the
real ASGI app, so the contract the Command Centre and the 5090 Studio worker depend
on is proven as a whole — not just endpoint-by-endpoint.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from invisable_os.main import app

client = TestClient(app)


def test_studio_worker_full_job_contract(tmp_path, monkeypatch):
    """The 5090 worker loop: create → claim-next → progress → upload → complete."""
    monkeypatch.setenv("INVISABLE_UPLOAD_DIR", str(tmp_path / "uploads"))

    # 1. Command Centre creates a render job.
    created = client.post(
        "/api/jobs/create",
        json={"kind": "ffmpeg_render", "title": "E2E cut", "priority": 1},
    ).json()["job"]
    job_id = created["id"]

    # 2. It shows on the render board the worker polls.
    board = client.get("/api/jobs/render").json()
    assert any(j["id"] == job_id for j in board["jobs"])

    # 3. Worker claims the next available job (the real loop uses next/claim).
    claim = client.post(
        "/api/jobs/next/claim", json={"worker_id": "studio-5090"}
    ).json()
    assert claim["ok"] and claim["job"]["id"] == job_id

    # 4. Worker reports progress as it processes.
    for p, msg in [(0.25, "step 2/8"), (0.75, "step 6/8")]:
        prog = client.post(
            f"/api/jobs/{job_id}/progress",
            json={"progress": p, "status": "processing", "log": msg},
        ).json()
        assert prog["job"]["progress"] == p

    # 5. Worker uploads the finished asset (multipart), tagged with the job id.
    files = {"file": ("final.mp4", io.BytesIO(b"rendered-bytes"), "video/mp4")}
    up = client.post(f"/api/assets/upload?job_id={job_id}", files=files).json()
    assert up["ok"] and up["bytes"] == len(b"rendered-bytes")

    # 6. Worker marks the job complete; the uploaded asset is on the result.
    done = client.post(
        f"/api/jobs/{job_id}/complete",
        json={"result": {"assets": [up["path"]]}},
    ).json()
    assert done["job"]["status"] == "completed"
    assert done["job"]["progress"] == 1.0

    # 7. The job no longer sits on the render board.
    board2 = client.get("/api/jobs/render").json()
    assert not any(j["id"] == job_id for j in board2["jobs"])


def test_command_centre_post_lifecycle_contract():
    """Command Centre: request content → edit → approve → schedule → on the calendar."""
    # 0. A channel with posting slots must exist for scheduling to land.
    client.post(
        "/v1/channels?with_default_schedule=true",
        json={"name": "INVISABLE IG", "platform": "instagram"},
    )

    # 1. Stephen requests specific content; the tournament queues a winner.
    req = client.post(
        "/api/content/request",
        json={"brief": "a warm post about pacing with chronic illness", "count": 1},
    ).json()
    assert req["ok"]
    assert req["queued_ids"], "content request must queue the winners"

    # Find the freshly queued, reviewable post.
    queue = client.get("/api/queue?status=pending_review").json()["items"]
    assert queue, "content request should have queued at least one post"
    post_id = queue[0]["id"]

    # 2. Edit its caption + hashtags (manual override).
    edited = client.post(
        f"/api/posts/{post_id}/edit",
        json={"caption": "Pacing isn't giving up — it's strategy.", "hashtags": ["#spoonie"]},
    ).json()
    assert edited["post"]["candidate"]["body"].startswith("Pacing")

    # 3. Approve → schedule → it appears on the calendar under its day.
    assert client.post(f"/api/posts/{post_id}/approve").json()["post"]["status"] == "approved"
    sched = client.post(f"/api/posts/{post_id}/schedule").json()
    assert sched["ok"]
    cal = client.get("/api/calendar").json()["calendar"]
    assert any(
        any(i["id"] == post_id for i in day_items) for day_items in cal.values()
    )


def test_emergency_pause_is_visible_in_status():
    """The top bar's emergency-pause indicator reflects an automation pause."""
    client.post("/api/automation/pause", json={"scope": "all", "reason": "e2e"})
    status = client.get("/api/system/status").json()
    assert status["emergency_pause"] is True
    assert status["automation_paused"] is True
    client.post("/api/automation/resume", json={"scope": "all"})
    assert client.get("/api/system/status").json()["emergency_pause"] is False
