"""Per-post attribution: split the Founder Recognition Index across the posts that earned it."""

from fastapi.testclient import TestClient

from invisable_os.engines import AlgorithmWatchtower
from invisable_os.main import app
from invisable_os.models.content import QueueStatus
from invisable_os.services import post_attribution
from invisable_os.store import get_repository

client = TestClient(app)


def _signal(candidate_id, metric, value):
    return {"candidate_id": candidate_id, "metric": metric, "value": value}


# --- Watchtower.attribute_recognition (pure) --------------------------------


def test_attribution_sums_back_to_the_index():
    wt = AlgorithmWatchtower()
    signals = [
        _signal("A", "media_mentions", 4),
        _signal("A", "podcast_invitations", 2),
        _signal("B", "media_mentions", 1),
        _signal("B", "profile_visits", 1000),
    ]
    ranked = wt.attribute_recognition(signals)
    totals = {"media_mentions": 5, "podcast_invitations": 2, "profile_visits": 1000}
    index = wt.founder_recognition_index(totals)

    # Exact allocation: per-post contributions sum back to the index.
    assert abs(sum(p["contribution"] for p in ranked) - index) < 1e-3
    # A (4 mentions + 2 podcast invites) outranks B.
    assert [p["candidate_id"] for p in ranked] == ["A", "B"]
    assert ranked[0]["breakdown"]["podcast_invitations"] > 0


def test_attribution_ignores_non_recognition_metrics():
    wt = AlgorithmWatchtower()
    # Saves/comments aren't recognition-bearing — they shouldn't be attributed.
    ranked = wt.attribute_recognition([
        _signal("A", "saves", 50),
        _signal("A", "comments", 30),
    ])
    assert ranked == []


def test_attribution_empty():
    assert AlgorithmWatchtower().attribute_recognition([]) == []


# --- service: joins post display text ---------------------------------------


def _enqueue(repo, candidate_id, hook):
    return repo.enqueue({
        "candidate_id": candidate_id,
        "candidate": {"hook": hook, "platform": "tiktok"},
        "status": QueueStatus.PUBLISHED.value,
        "platform": "tiktok",
    })


def test_post_attribution_joins_hooks():
    repo = get_repository()
    _enqueue(repo, "cand-A", "Why I started INVISABLE.")
    _enqueue(repo, "cand-B", "Looks fine, but I'm not.")
    repo.record_signal("cand-A", "tiktok", "media_mentions", 3.0, ["founder"])
    repo.record_signal("cand-B", "tiktok", "profile_visits", 500.0, ["awareness"])

    out = post_attribution()
    assert out["attributed_posts"] == 2
    top = out["posts"][0]
    assert top["candidate_id"] == "cand-A"
    assert top["hook"] == "Why I started INVISABLE."
    assert top["platform"] == "tiktok"
    assert out["index"] > 0


def test_post_attribution_empty_when_no_signals():
    out = post_attribution()
    assert out == {"index": 0.0, "attributed_posts": 0, "posts": []}


# --- endpoint ---------------------------------------------------------------


def test_recognition_by_post_endpoint():
    repo = get_repository()
    _enqueue(repo, "cand-X", "The audacity of fatigue.")
    repo.record_signal("cand-X", "instagram", "speaking_opportunities", 2.0, [])

    r = client.get("/v1/founder/recognition/by-post?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["attributed_posts"] == 1
    assert body["posts"][0]["hook"] == "The audacity of fatigue."
