"""The /api/* desktop surface: status, render-job lifecycle, automation, content."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.store import get_repository

client = TestClient(app)


def test_health_is_open_and_reports_auth_posture():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "invisable-media"
    assert body["auth_required"] is False  # no token configured in tests


def test_system_status_snapshot_shape():
    r = client.get("/api/system/status")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "queue_counts",
        "pending_jobs",
        "failed_jobs",
        "posts_scheduled_today",
        "automation_paused",
        "posting_paused",
        "integrations",
    ):
        assert key in body, key


def test_render_job_full_lifecycle():
    # Create
    r = client.post(
        "/api/jobs/create",
        json={"kind": "ffmpeg_render", "title": "Test cut", "priority": 1},
    )
    assert r.status_code == 200
    job = r.json()["job"]
    job_id = job["id"]
    assert job["status"] == "queued"

    # Appears on the render board
    board = client.get("/api/jobs/render").json()
    assert any(j["id"] == job_id for j in board["jobs"])

    # Worker claims the next job
    claim = client.post(
        "/api/jobs/next/claim", json={"worker_id": "studio-5090"}
    ).json()
    assert claim["ok"] is True
    assert claim["job"]["id"] == job_id
    assert claim["job"]["worker_id"] == "studio-5090"

    # Progress
    prog = client.post(
        f"/api/jobs/{job_id}/progress",
        json={"progress": 0.5, "status": "processing", "log": "halfway"},
    ).json()
    assert prog["job"]["progress"] == 0.5
    assert "halfway" in prog["job"]["logs"]

    # Complete
    done = client.post(
        f"/api/jobs/{job_id}/complete",
        json={"result": {"assets": ["/srv/out.mp4"]}},
    ).json()
    assert done["job"]["status"] == "completed"
    assert done["job"]["progress"] == 1.0


def test_unknown_job_kind_rejected():
    r = client.post("/api/jobs/create", json={"kind": "not_a_real_kind"})
    assert r.status_code == 422


def test_asset_upload_registers_file(tmp_path, monkeypatch):
    monkeypatch.setenv("INVISABLE_UPLOAD_DIR", str(tmp_path / "uploads"))
    job = client.post(
        "/api/jobs/create", json={"kind": "upload", "title": "u"}
    ).json()["job"]
    files = {"file": ("final.mp4", io.BytesIO(b"video-bytes"), "video/mp4")}
    r = client.post(f"/api/assets/upload?job_id={job['id']}", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["bytes"] == len(b"video-bytes")
    assert body["filename"] == "final.mp4"


def test_automation_pause_and_resume():
    paused = client.post(
        "/api/automation/pause", json={"scope": "all", "reason": "test"}
    ).json()
    assert paused["state"]["automation_paused"] is True

    status = client.get("/api/system/status").json()
    assert status["automation_paused"] is True
    assert status["emergency_pause"] is True

    resumed = client.post("/api/automation/resume", json={"scope": "all"}).json()
    assert resumed["state"]["automation_paused"] is False


def test_posting_pause_is_independent_of_automation():
    client.post("/api/automation/pause", json={"scope": "posting"})
    status = client.get("/api/system/status").json()
    assert status["posting_paused"] is True
    assert status["automation_paused"] is False
    client.post("/api/automation/resume", json={"scope": "posting"})


def test_content_request_runs_tournament_and_queues():
    r = client.post(
        "/api/content/request",
        json={"brief": "A warm post about invisible illness", "count": 1},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "tournament" in body
    assert body["render_job"] is not None


def test_post_approve_and_reject_transitions():
    # Seed a queue item directly through the repository.
    repo = get_repository()
    item_id = repo.enqueue(
        {
            "candidate_id": "c1",
            "candidate": {"brief": "x", "body": "hello"},
            "status": "pending_review",
            "platform": "instagram",
        }
    )
    r = client.post(f"/api/posts/{item_id}/approve")
    assert r.status_code == 200
    assert r.json()["post"]["status"] == "approved"

    r = client.post(f"/api/posts/{item_id}/reject", json={"reason": "off-brand"})
    assert r.json()["post"]["status"] == "rejected"


def test_post_action_on_missing_id_is_404():
    r = client.post("/api/posts/does-not-exist/approve")
    assert r.status_code == 404
