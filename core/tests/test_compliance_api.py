"""The /api/compliance/* surface — Platform Health, events, mode, emergency buttons."""

from __future__ import annotations

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.store import get_repository

client = TestClient(app)


def test_health_report_shape_default_low_risk():
    r = client.get("/api/compliance/health")
    assert r.status_code == 200
    body = r.json()
    for key in ("health_score", "risk_level", "mode", "suggested_mode", "findings",
                "shadowban_signals", "recommended_action", "mode_limits", "modes"):
        assert key in body, key
    # A clean, empty account defaults to introduction mode, low risk.
    assert body["mode"] == "introduction"
    assert body["risk_level"] == "low"


def test_record_event_and_it_drives_risk():
    # A platform warning should push risk up to at least HIGH.
    client.post("/api/compliance/events", json={"kind": "warning", "platform": "instagram"})
    body = client.get("/api/compliance/health").json()
    assert body["risk_level"] in ("high", "critical")
    assert any(f["monitor"] == "platform_warning" for f in body["findings"])


def test_events_listing():
    client.post("/api/compliance/events", json={"kind": "api_error"})
    events = client.get("/api/compliance/events").json()["events"]
    assert any(e["kind"] == "api_error" for e in events)


def test_set_mode_and_reject_unknown():
    ok = client.post("/api/compliance/mode", json={"mode": "active_influencer"})
    assert ok.status_code == 200
    assert ok.json()["mode"] == "active_influencer"

    bad = client.post("/api/compliance/mode", json={"mode": "turbo"})
    assert bad.status_code == 422


def test_evaluate_enforces_downgrade_and_pause_on_high_risk():
    # Seed several published posts today to blow past the introduction limit.
    repo = get_repository()
    from invisable_os.models.content import QueueStatus

    client.post("/api/compliance/mode", json={"mode": "introduction"})
    for i in range(5):
        item_id = repo.enqueue(
            {"candidate_id": f"c{i}", "candidate": {"body": f"post {i}"}, "platform": "instagram"}
        )
        repo.transition(item_id, QueueStatus.PUBLISHED)

    out = client.post("/api/compliance/evaluate").json()
    assert out["risk_level"] in ("high", "critical")
    # Over-limit forces a downgrade and pauses automation.
    assert out["mode"] in ("manual_only",) or "mode →" in " ".join(out["enforced"])
    status = client.get("/api/system/status").json()
    assert status["automation_paused"] is True


def test_emergency_buttons_only_stop_things():
    for action in [
        "stop_comments",
        "stop_reposts",
        "stop_story_pushes",
        "stop_scheduling",
    ]:
        r = client.post("/api/compliance/emergency", json={"action": action}).json()
        assert r["ok"]
    switches = client.get("/api/compliance/health").json()["switches"]
    assert switches.get("comments_stopped") is True
    assert switches.get("scheduling_stopped") is True


def test_manual_only_and_account_cooldown():
    client.post("/api/compliance/emergency", json={"action": "manual_only"})
    assert client.get("/api/compliance/health").json()["mode"] == "manual_only"

    client.post("/api/compliance/emergency", json={"action": "account_cooldown"})
    status = client.get("/api/system/status").json()
    assert status["automation_paused"] is True
    assert status["posting_paused"] is True


def test_clear_today_queue_rejects_todays_posts():
    repo = get_repository()
    item_id = repo.enqueue(
        {"candidate_id": "ctoday", "candidate": {"body": "today"}, "platform": "instagram"}
    )
    out = client.post("/api/compliance/emergency", json={"action": "clear_today_queue"}).json()
    assert out["cleared"] >= 1
    assert repo.get_queue_item(item_id)["status"] == "rejected"


def test_unknown_emergency_action_422():
    r = client.post("/api/compliance/emergency", json={"action": "nuke"})
    assert r.status_code == 422


def test_system_status_carries_watchdog_fields():
    s = client.get("/api/system/status").json()
    for key in ("compliance_risk", "posting_mode", "account_health"):
        assert key in s, key
