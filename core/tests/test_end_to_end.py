"""End-to-end integration — the whole program works *inside the dashboard*.

These exercise the real HTTP surface the PWA and desktop window call, driving one
piece of content through the entire lifecycle:

    seed channel → swarm cycle (scan→generate→gate→stock) → approve → schedule →
    calendar → War Chest draw → produce media → fact-check → remix

If any seam between the engines, services, store and API breaks, these fail — so the
parallel feature work can't silently regress the working machine.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.services import run_self_check

client = TestClient(app)


def test_full_content_lifecycle_through_the_api():
    # 1. Seed a channel + posting schedule.
    seeded = client.post(
        "/v1/channels", json={"name": "E2E TikTok", "platform": "tiktok"}
    ).json()
    assert seeded["slots_created"] > 0

    # 2. Run a swarm cycle: scan → generate → gate → stock.
    cycle = client.post(
        "/v1/swarm/run", json={"drafts_per_topic": 1, "live_sources": False}
    ).json()
    funnel = cycle["funnel"]
    assert funnel["raw_drafts"] > 0
    assert funnel["usable_drafts_queued"] > 0

    # 3. The queue holds the usable drafts.
    queue = client.get("/v1/queue?status=pending_review").json()
    assert queue["items"], "swarm produced no queued drafts"
    item_id = queue["items"][0]["id"]

    # 4. Approve it.
    approved = client.post(f"/v1/queue/{item_id}/approve").json()
    assert approved["status"] == "approved"

    # 5. Schedule it onto the next open slot.
    scheduled = client.post(f"/v1/queue/{item_id}/schedule-next").json()
    assert "scheduled_at" in scheduled, scheduled

    # 6. The calendar reflects it.
    cal = client.get("/v1/calendar").json()["calendar"]
    assert len(cal) >= 1

    # 7. Produce its media assets (the flywheel).
    produced = client.post(f"/v1/media/produce/{item_id}").json()
    assert produced.get("produced", 0) > 0
    assert client.get("/v1/media").json()["assets"]


def test_war_chest_and_fact_check_seams():
    client.post("/v1/swarm/run", json={"drafts_per_topic": 1, "live_sources": False})
    client.post("/v1/warchest/stock")

    health = client.get("/v1/warchest").json()
    assert "tier" in health and "recommended_posts_per_day" in health

    # A fact-led claim with no source must be flagged by the Credible Source Rule.
    fc = client.post(
        "/v1/factcheck",
        json={"text": "Tool theft rose 20% in 2024 according to official figures."},
    ).json()
    assert fc["fact_led"] is True
    assert fc["ok"] is False


def test_remix_and_scanner_seams():
    parody = client.post(
        "/v1/remix/create", json={"mode": "create_parody", "topic": "tool theft", "persist": True}
    ).json()
    assert parody.get("job_id") is not None

    scanned = client.post(
        "/v1/scanner/manual-link", json={"url": "https://tiktok.com/@x/video/1"}
    ).json()
    assert scanned["reference"]["rights_status"] == "reference_only"
    assert len(scanned["suggested_angles"]) == 5


def test_every_dashboard_screen_endpoint_responds():
    # The read endpoints behind each of the dashboard's tabs must all answer 200.
    for path in (
        "/v1/values", "/v1/personality/mix", "/v1/brain/stats", "/v1/agents",
        "/v1/queue", "/v1/calendar", "/v1/media",
        "/v1/warchest", "/v1/warchest/items",
        "/v1/sources", "/v1/sources/hierarchy",
        "/v1/swarm/bots", "/v1/swarm/stats", "/v1/swarm/topics?live=false",
        "/v1/scanner/items", "/v1/remix/modes", "/v1/rights", "/v1/rights-assets",
        "/v1/popculture", "/v1/meme-formats", "/v1/founder/recognition",
    ):
        assert client.get(path).status_code == 200, path


def test_self_check_service_reports_all_green():
    # The same pipeline the `invisable doctor` command runs.
    report = run_self_check()
    assert report.ok, [s.detail for s in report.stages if not s.ok]
    assert report.as_dict()["passed"] == report.as_dict()["total"]
