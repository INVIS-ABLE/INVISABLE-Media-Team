"""The 5090 Studio Engine: local, offline content generation + review + export."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from invisable_os.engines.studio import BATCHES, DAILY20_MIX, StudioEngine
from invisable_os.main import app
from invisable_os.models.studio import StudioStatus
from invisable_os.studio.store import StudioStore

client = TestClient(app)


# --- engine: generation -----------------------------------------------------


def test_daily20_generates_exactly_twenty_posts():
    posts = StudioEngine().generate_daily20()
    assert len(posts) == 20
    assert len(DAILY20_MIX) == 20


@pytest.mark.parametrize("batch", list(BATCHES))
def test_each_named_batch_generates_requested_count(batch):
    posts = StudioEngine().generate_batch(batch, count=4)
    assert len(posts) == 4
    assert all(p.batch == batch for p in posts)


def test_unknown_batch_raises():
    with pytest.raises(ValueError):
        StudioEngine().generate_batch("does-not-exist")


def test_every_post_has_all_required_fields():
    post = StudioEngine().generate_batch("awareness", count=1)[0]
    assert post.platform and post.format  # enums are truthy
    assert post.hook
    assert post.caption
    assert post.hashtags and all(h.startswith("#") for h in post.hashtags)
    assert post.script
    assert post.visual_idea
    assert post.founder_presence_suggestion


def test_scores_are_present_and_bounded():
    for post in StudioEngine().generate_daily20():
        for value in (
            post.risk_score, post.mission_score, post.humour_score, post.authenticity_score
        ):
            assert 0.0 <= value <= 1.0


def test_founder_batch_centres_the_founder_and_suggests_him_on_camera():
    post = StudioEngine().generate_batch("founder", count=1)[0]
    assert post.founder_centred is True
    assert "stephen" in post.founder_presence_suggestion.lower()


def test_humour_batch_scores_humour_above_zero():
    posts = StudioEngine().generate_batch("humour", count=3)
    assert any(p.humour_score > 0 for p in posts)


def test_offline_content_is_original_and_safe():
    # No model configured in tests → deterministic templates. Must never be flagged.
    for post in StudioEngine().generate_daily20():
        assert post.original is True
        assert post.risk_score < 1.0  # nothing blocked
        assert not post.notes  # no guardrail violations recorded


# --- store: save / review / export round-trip -------------------------------


def test_store_saves_to_generated_folder(tmp_path):
    store = StudioStore(base_dir=tmp_path)
    posts = StudioEngine().generate_batch("humour", count=3)
    store.save_batch(posts)
    assert store.stats()["generated"] == 3
    assert (tmp_path / "generated").is_dir()
    for p in posts:
        assert p.created_at  # stamped on save


def test_approve_moves_post_between_folders(tmp_path):
    store = StudioStore(base_dir=tmp_path)
    posts = store.save_batch(StudioEngine().generate_batch("awareness", count=2))
    store.approve(posts[0].id)
    assert store.stats() == {
        "generated": 1, "approved": 1, "rejected": 0, "ready_to_post": 0
    }
    moved = store.get(posts[0].id)
    assert moved.status == StudioStatus.APPROVED
    # The old file is gone from generated.
    assert not (tmp_path / "generated" / f"{posts[0].id}.json").exists()


def test_reject_moves_post_to_rejected(tmp_path):
    store = StudioStore(base_dir=tmp_path)
    posts = store.save_batch(StudioEngine().generate_batch("trend", count=1))
    store.reject(posts[0].id)
    assert store.get(posts[0].id).status == StudioStatus.REJECTED


def test_edit_updates_editable_fields_only(tmp_path):
    store = StudioStore(base_dir=tmp_path)
    posts = store.save_batch(StudioEngine().generate_batch("community", count=1))
    pid = posts[0].id
    edited = store.edit(pid, {"hook": "A brand new hook", "id": "hacked", "risk_score": 9})
    assert edited.hook == "A brand new hook"
    assert edited.id == pid  # id is not editable
    assert store.get(pid).hook == "A brand new hook"


def test_export_approved_packages_to_ready_to_post(tmp_path):
    store = StudioStore(base_dir=tmp_path)
    posts = store.save_batch(StudioEngine().generate_batch("founder", count=3))
    store.approve(posts[0].id)
    store.approve(posts[1].id)
    result = store.export_approved()
    assert result["exported"] == 2
    assert store.stats()["ready_to_post"] == 2
    assert store.stats()["approved"] == 0
    # A paste-ready markdown sits next to each exported JSON.
    md_files = list((tmp_path / "ready_to_post").glob("*.md"))
    assert len(md_files) == 2
    assert "## Caption" in md_files[0].read_text(encoding="utf-8")


def test_get_unknown_post_returns_none(tmp_path):
    assert StudioStore(base_dir=tmp_path).get("nope") is None


# --- API surface ------------------------------------------------------------


def test_api_generate_then_list_then_approve_then_export():
    gen = client.post("/v1/studio/generate", json={"batch": "humour", "count": 3}).json()
    assert gen["generated"] == 3
    first = gen["posts"][0]
    # Scores are hoisted to the top level for the UI.
    for key in ("risk_score", "mission_score", "humour_score", "authenticity_score"):
        assert key in first

    listed = client.get("/v1/studio/posts", params={"status": "generated"}).json()
    assert listed["counts"]["generated"] >= 3

    approved = client.post(f"/v1/studio/posts/{first['id']}/approve").json()
    assert approved["ok"] is True
    assert approved["post"]["status"] == "approved"

    exported = client.post("/v1/studio/export").json()
    assert exported["exported"] >= 1


def test_api_generate_daily20():
    data = client.post("/v1/studio/generate", json={"batch": "daily20"}).json()
    assert data["generated"] == 20


def test_api_unknown_batch_returns_error():
    data = client.post("/v1/studio/generate", json={"batch": "bogus"}).json()
    assert "error" in data


def test_api_reject_and_edit():
    gen = client.post("/v1/studio/generate", json={"batch": "trend", "count": 1}).json()
    pid = gen["posts"][0]["id"]
    edited = client.post(
        f"/v1/studio/posts/{pid}/edit", json={"fields": {"caption": "Edited caption"}}
    ).json()
    assert edited["post"]["caption"] == "Edited caption"
    rejected = client.post(f"/v1/studio/posts/{pid}/reject").json()
    assert rejected["post"]["status"] == "rejected"
