"""HTTP surface for the Remix department (runs against the isolated test DB)."""

from fastapi.testclient import TestClient

from invisable_os.main import app

client = TestClient(app)


def test_rights_endpoint_lists_usable_statuses():
    body = client.get("/v1/rights").json()
    assert set(body["usable_in_media"]) == {
        "owned", "licensed", "public_domain",
        "creative_commons", "user_submitted_consent", "platform_duet_stitch",
    }
    assert "reference_only" in body["never_use"]


def test_modes_endpoint_lists_fifteen_buttons():
    body = client.get("/v1/remix/modes").json()
    assert len(body["scan_modes"]) == 6
    assert len(body["create_modes"]) == 9


def test_scan_persists_to_reference_inbox():
    r = client.post("/v1/scanner/scan", json={"mode": "scan_tool_theft"})
    assert r.status_code == 200
    assert r.json()["count"] >= 1
    inbox = client.get("/v1/scanner/items").json()["items"]
    assert inbox and all(i["rights_status"] == "reference_only" for i in inbox)


def test_manual_link_defaults_reference_only_and_suggests_angles():
    r = client.post(
        "/v1/scanner/manual-link",
        json={"url": "https://www.youtube.com/watch?v=abc", "topic": "tool theft"},
    ).json()
    assert r["reference"]["rights_status"] == "reference_only"
    assert r["download_plan"]["allowed"] is False
    assert len(r["suggested_angles"]) == 5


def test_remix_create_queues_a_job():
    r = client.post(
        "/v1/remix/create",
        json={"mode": "create_parody", "topic": "tool theft and invisible illness"},
    ).json()
    assert r["pack"]["brand_safe"] is True
    assert r["job_id"]
    jobs = client.get("/v1/remix/jobs").json()["jobs"]
    assert any(j["id"] == r["job_id"] for j in jobs)


def test_voiceover_blocked_over_reference_only_asset():
    owned = client.post(
        "/v1/media/upload", json={"title": "van", "rights_status": "owned", "file_path": "/v.mp4"}
    ).json()["id"]
    ref = client.post(
        "/v1/media/upload", json={"title": "ripped", "rights_status": "reference_only"}
    ).json()["id"]

    ok = client.post(
        "/v1/voiceover/create", json={"asset_id": owned, "script": "trades fatigue bit"}
    ).json()
    assert ok["blocked_reason"] == ""

    blocked = client.post(
        "/v1/voiceover/create", json={"asset_id": ref, "script": "x"}
    ).json()
    assert blocked["blocked_reason"]


def test_patch_media_rights():
    aid = client.post(
        "/v1/media/upload", json={"title": "clip", "rights_status": "reference_only"}
    ).json()["id"]
    upd = client.patch(
        f"/v1/media/{aid}/rights", json={"rights_status": "licensed", "licence_notes": "deal"}
    ).json()
    assert upd["rights_status"] == "licensed"


def test_rights_check_endpoint_blocks_unusable():
    body = client.post(
        "/v1/rights/check",
        json={"assets": [{"title": "ripped", "rights_status": "reference_only"}]},
    ).json()
    assert body["passed"] is False
