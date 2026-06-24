"""finish_post: approve → produce → assemble (→ DAM) so the video is ready before its slot."""

from fastapi.testclient import TestClient

from invisable_os.main import app
from invisable_os.models.content import QueueStatus
from invisable_os.services import finish_post
from invisable_os.store import get_repository

client = TestClient(app)


def _enqueue(repo, candidate_id="cf", status=QueueStatus.PENDING_REVIEW):
    return repo.enqueue({
        "candidate_id": candidate_id,
        "candidate": {"brief": "Tool theft again", "platform": "tiktok", "hook": "Not again."},
        "status": status.value,
        "platform": "tiktok",
    })


# --- service ----------------------------------------------------------------


def test_finish_post_produces_and_assembles():
    repo = get_repository()
    item_id = _enqueue(repo)

    report = finish_post(item_id)

    # Flywheel assets were produced and a final cutdown was assembled.
    assert report["item_id"] == item_id
    assert report["produced"] >= 5
    assert report["final_video"]
    assert report["assemble_backend"]  # ffmpeg or dry-run, never empty
    assert "dam" not in report  # DAM only runs when asked
    # The library now holds the produced assets plus exactly one final_video.
    finals = [a for a in repo.list_media(item_id) if a["kind"] == "final_video"]
    assert len(finals) == 1


def test_finish_post_with_dam_archives():
    repo = get_repository()
    item_id = _enqueue(repo, candidate_id="cf-dam")

    report = finish_post(item_id, dam=True)

    assert report["final_video"]
    assert "dam" in report
    assert report["dam"]["backend"] in {"resourcespace", "dry-run"}
    assert report["dam"]["count"] >= 0


def test_finish_post_missing_item():
    assert "error" in finish_post("does-not-exist")


# --- endpoint ---------------------------------------------------------------


def test_media_finish_endpoint():
    repo = get_repository()
    item_id = _enqueue(repo, candidate_id="cf-api")

    r = client.post(f"/v1/media/finish/{item_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["item_id"] == item_id
    assert body["produced"] >= 5
    assert body["final_video"]


def test_media_finish_endpoint_with_dam():
    repo = get_repository()
    item_id = _enqueue(repo, candidate_id="cf-api-dam")

    r = client.post(f"/v1/media/finish/{item_id}?dam=true")
    assert r.status_code == 200
    assert "dam" in r.json()


def test_media_finish_endpoint_missing_item():
    assert "error" in client.post("/v1/media/finish/nope").json()


# --- approve?finish=true wiring ---------------------------------------------


def test_approve_with_finish_triggers_production():
    repo = get_repository()
    item_id = _enqueue(repo, candidate_id="cf-approve")

    r = client.post(f"/v1/queue/{item_id}/approve?finish=true")
    assert r.status_code == 200
    body = r.json()
    # The item is approved AND carries the finish report.
    assert body["status"] == QueueStatus.APPROVED.value
    assert "finished" in body
    assert body["finished"]["produced"] >= 5
    assert body["finished"]["final_video"]


def test_approve_without_finish_does_not_produce():
    repo = get_repository()
    item_id = _enqueue(repo, candidate_id="cf-plain")

    r = client.post(f"/v1/queue/{item_id}/approve")
    assert r.status_code == 200
    assert "finished" not in r.json()
    assert repo.list_media(item_id) == []
