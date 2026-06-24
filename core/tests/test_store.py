from invisable_os.models.content import QueueStatus
from invisable_os.models.departments import Opportunity, Partner, TagNetworkMember
from invisable_os.store import get_repository


def _item(hook="hello", pillar="humour", quality=7.0, passes=False):
    return {
        "candidate_id": "cand-1",
        "candidate": {"hook": hook, "body": "b", "platform": "instagram"},
        "status": QueueStatus.PENDING_REVIEW.value,
        "pillar": pillar,
        "platform": "instagram",
        "quality_avg": quality,
        "quality_passes": passes,
        "mission_total": 0.4,
        "mission_verdict": "hold",
        "tags": ["@x"],
        "asset_count": 7,
    }


def test_enqueue_and_list():
    repo = get_repository()
    item_id = repo.enqueue(_item())
    items = repo.list_queue()
    assert len(items) == 1
    assert items[0]["id"] == item_id
    assert items[0]["status"] == "pending_review"
    assert items[0]["asset_count"] == 7


def test_filter_by_status_and_counts():
    repo = get_repository()
    repo.enqueue(_item(hook="a"))
    repo.enqueue({**_item(hook="b"), "status": QueueStatus.NEEDS_IMPROVEMENT.value})
    assert len(repo.list_queue(status="pending_review")) == 1
    counts = repo.counts_by_status()
    assert counts["pending_review"] == 1
    assert counts["needs_improvement"] == 1


def test_lifecycle_transition_stamps_timestamps():
    repo = get_repository()
    item_id = repo.enqueue(_item())
    approved = repo.transition(item_id, QueueStatus.APPROVED)
    assert approved["status"] == "approved"
    published = repo.transition(item_id, QueueStatus.PUBLISHED)
    assert published["status"] == "published"
    assert published["published_at"] is not None


def test_transition_missing_item_returns_none():
    assert get_repository().transition("nope", QueueStatus.APPROVED) is None


def test_tag_member_round_trip():
    repo = get_repository()
    repo.add_tag_member(TagNetworkMember(display_name="Bald Builders", instagram_handle="@bb"))
    members = repo.list_tag_members()
    assert len(members) == 1
    assert members[0].display_name == "Bald Builders"


def test_partner_and_opportunity_persistence():
    repo = get_repository()
    repo.add_partner(Partner(name="CT1", sector="tools"))
    repo.record_opportunity(Opportunity(kind="podcast", title="Trades pod", fit_score=0.8))
    assert repo.list_partners()[0]["name"] == "CT1"
    assert repo.list_opportunities()[0]["kind"] == "podcast"
